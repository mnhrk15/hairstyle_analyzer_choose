"""
GeminiServiceのユニットテスト
"""

import os
import json
import unittest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import types

from hairstyle_analyzer.services.gemini.gemini_service import GeminiService
from hairstyle_analyzer.data.models import GeminiConfig, StyleAnalysis, AttributeAnalysis, StyleFeatures, StylistInfo, CouponInfo
from hairstyle_analyzer.utils.errors import GeminiAPIError, ImageError


class AsyncioTestCase(unittest.TestCase):
    """非同期テスト用のベースクラス"""
    
    async def asyncSetUp(self):
        """非同期セットアップ（オーバーライド可能）"""
        pass
    
    async def asyncTearDown(self):
        """非同期クリーンアップ（オーバーライド可能）"""
        pass
    
    def setUp(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.asyncSetUp())
    
    def tearDown(self):
        self.loop.run_until_complete(self.asyncTearDown())
        self.loop.close()
    
    def run_async(self, coroutine):
        """コルーチンを現在のイベントループで実行"""
        return self.loop.run_until_complete(coroutine)


class TestGeminiService(AsyncioTestCase):
    """GeminiServiceのテストケース"""
    
    def setUp(self):
        """テストの前処理"""
        super().setUp()
        
        # テスト用設定
        self.config = GeminiConfig(
            api_key="test_api_key",
            model="gemini-2.0-flash",
            fallback_model="gemini-2.0-flash-lite",
            max_tokens=300,
            temperature=0.7,
            prompt_template="テスト{categories}",
            attribute_prompt_template="テスト{length_choices}",
            stylist_prompt_template="テスト{stylists}{category}{color}{cut_technique}{styling}{impression}",
            coupon_prompt_template="テスト{coupons}{category}{color}{cut_technique}{styling}{impression}",
            length_choices=["ショート", "ミディアム", "ロング"]
        )
        
        # テスト用ダミー画像
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_image = Path(self.temp_dir.name) / "test_image.jpg"
        
        # ダミー画像作成（空ファイル）
        with open(self.temp_image, 'wb') as f:
            f.write(b'dummy image data')
        
        # GenAIモジュールのモック
        self.genai_mock = patch('hairstyle_analyzer.services.gemini.gemini_service.genai').start()
        self.model_mock = MagicMock()
        self.fallback_model_mock = MagicMock()
        self.genai_mock.GenerativeModel.side_effect = [self.model_mock, self.fallback_model_mock]
        
        # テスト対象のインスタンス作成
        self.service = GeminiService(self.config)
    
    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリの削除
        self.temp_dir.cleanup()
        
        # モックの停止
        patch.stopall()
        
        super().tearDown()
    
    def test_init(self):
        """初期化テスト"""
        # APIキーが設定されていることを確認
        self.genai_mock.configure.assert_called_once_with(api_key="test_api_key")
        
        # モデルが初期化されていることを確認
        self.genai_mock.GenerativeModel.assert_any_call("gemini-2.0-flash")
        self.genai_mock.GenerativeModel.assert_any_call("gemini-2.0-flash-lite")
    
    def test_init_no_api_key(self):
        """APIキーなしの初期化テスト"""
        # APIキーがない設定
        config_no_key = GeminiConfig(
            api_key="",
            model="gemini-2.0-flash",
            fallback_model="gemini-2.0-flash-lite",
            max_tokens=300,
            temperature=0.7,
            prompt_template="テスト{categories}",
            attribute_prompt_template="テスト{length_choices}",
            stylist_prompt_template="テスト{stylists}{category}{color}{cut_technique}{styling}{impression}",
            coupon_prompt_template="テスト{coupons}{category}{color}{cut_technique}{styling}{impression}",
            length_choices=["ショート", "ミディアム", "ロング"]
        )
        
        # 例外が発生することを確認
        with self.assertRaises(GeminiAPIError) as cm:
            GeminiService(config_no_key)
        
        # エラーメッセージを確認
        self.assertIn("APIキーが設定されていません", str(cm.exception))
    
    def test_format_prompt(self):
        """プロンプトフォーマットテスト"""
        # 変数の置換テスト
        template = "カテゴリ: {categories}, 長さ: {lengths}"
        formatted = self.service._format_prompt(
            template=template,
            categories="テストカテゴリ",
            lengths="テスト長さ"
        )
        
        # フォーマット結果を確認
        self.assertEqual(formatted, "カテゴリ: テストカテゴリ, 長さ: テスト長さ")
    
    def test_format_prompt_missing_var(self):
        """存在しない変数のプロンプトフォーマットテスト"""
        # 存在しない変数を使用
        template = "カテゴリ: {categories}, 存在しない: {nonexistent}"
        
        # エラーが発生せず、テンプレートがそのまま返されることを確認
        formatted = self.service._format_prompt(
            template=template,
            categories="テストカテゴリ"
        )
        
        # 元のテンプレートがそのまま返されることを確認
        self.assertEqual(formatted, template)
    
    def test_prepare_image(self):
        """画像準備テスト"""
        # encode_imageと画像検証のモック
        with patch('hairstyle_analyzer.services.gemini.gemini_service.encode_image',
                  return_value="base64_encoded_data"), \
             patch('hairstyle_analyzer.services.gemini.gemini_service.is_valid_image',
                  return_value=True):
            
            # 画像準備
            result = self.service._prepare_image(self.temp_image)
            
            # 結果を確認
            self.assertEqual(result, {
                "mime_type": "image/jpeg",
                "data": "base64_encoded_data"
            })
    
    def test_prepare_image_invalid(self):
        """無効な画像の準備テスト"""
        # 無効な画像としてモック
        with patch('hairstyle_analyzer.services.gemini.gemini_service.is_valid_image',
                  return_value=False):
            
            # 例外が発生することを確認
            with self.assertRaises(ImageError) as cm:
                self.service._prepare_image(self.temp_image)
            
            # エラーメッセージを確認
            self.assertIn("無効な画像ファイル", str(cm.exception))
    
    def test_parse_json_response(self):
        """JSONレスポンスのパースタスト"""
        # 有効なJSONレスポンス
        json_response = '{"key": "value", "number": 123}'
        
        # パース
        result = self.service._parse_json_response(json_response)
        
        # 結果を確認
        self.assertEqual(result, {"key": "value", "number": 123})
    
    def test_parse_json_response_invalid(self):
        """無効なJSONレスポンスのパーステスト"""
        # 無効なJSONレスポンス
        invalid_json = '{"key": "value", error here}'
        
        # 例外が発生することを確認
        with self.assertRaises(GeminiAPIError) as cm:
            self.service._parse_json_response(invalid_json)
        
        # エラーメッセージを確認
        self.assertIn("APIレスポンスのJSONパースに失敗", str(cm.exception))
    
    def test_call_gemini_api(self):
        """非同期API呼び出しテスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # run_in_executor の結果をモック
            response_mock = MagicMock()
            response_mock.text = '{"test": "response"}'
            future = asyncio.Future()
            future.set_result(response_mock)
            mock_loop.run_in_executor.return_value = future
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # API呼び出し
                result = self.run_async(self.service._call_gemini_api("テストプロンプト", self.temp_image))
                
                # 結果を確認
                self.assertEqual(result, '{"test": "response"}')
                
                # モデルの generate_content が正しく呼び出されたことを確認
                mock_loop.run_in_executor.assert_called_once()
    
    def test_call_gemini_api_retry(self):
        """非同期API呼び出しリトライテスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop, \
             patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.sleep', return_value=None) as mock_sleep:
            
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # 最初の2回は例外を発生させるFutureを作成し、3回目で成功するFutureを作成
            error_future1 = asyncio.Future()
            error_future1.set_exception(Exception("API error 1"))
            
            error_future2 = asyncio.Future()
            error_future2.set_exception(Exception("API error 2"))
            
            success_future = asyncio.Future()
            success_response = MagicMock()
            success_response.text = '{"test": "response"}'
            success_future.set_result(success_response)
            
            # run_in_executor の side_effect を設定
            mock_loop.run_in_executor.side_effect = [error_future1, error_future2, success_future]
            
            # リトライ回数を設定
            self.service.config.max_retries = 3
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # API呼び出し
                result = self.run_async(self.service._call_gemini_api("テストプロンプト", self.temp_image))
                
                # 結果を確認
                self.assertEqual(result, '{"test": "response"}')
                
                # sleepが2回呼ばれたことを確認（リトライの一部）
                self.assertEqual(mock_sleep.call_count, 2)
                
                # run_in_executor が3回呼ばれたことを確認
                self.assertEqual(mock_loop.run_in_executor.call_count, 3)
    
    def test_call_gemini_api_fallback(self):
        """非同期API呼び出しフォールバックテスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop, \
             patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.sleep', return_value=None) as mock_sleep:
            
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # プライマリモデルのすべての試行で失敗するFutureを作成
            error_future1 = asyncio.Future()
            error_future1.set_exception(Exception("Primary model error 1"))
            
            error_future2 = asyncio.Future()
            error_future2.set_exception(Exception("Primary model error 2"))
            
            error_future3 = asyncio.Future()
            error_future3.set_exception(Exception("Primary model error 3"))
            
            # フォールバックモデルで成功するFutureを作成
            success_future = asyncio.Future()
            success_response = MagicMock()
            success_response.text = '{"test": "fallback_response"}'
            success_future.set_result(success_response)
            
            # run_in_executor の side_effect を設定
            mock_loop.run_in_executor.side_effect = [error_future1, error_future2, error_future3, success_future]
            
            # リトライ回数を設定
            self.service.config.max_retries = 3
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # API呼び出し
                result = self.run_async(self.service._call_gemini_api("テストプロンプト", self.temp_image))
                
                # 結果を確認
                self.assertEqual(result, '{"test": "fallback_response"}')
                
                # sleepが2回呼ばれたことを確認（プライマリモデルでの2回のリトライ）
                self.assertEqual(mock_sleep.call_count, 2)
                
                # run_in_executor が4回呼ばれたことを確認（プライマリ3回+フォールバック1回）
                self.assertEqual(mock_loop.run_in_executor.call_count, 4)
    
    def test_analyze_image(self):
        """画像分析テスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # API呼び出しの結果をモック
            response_json = {
                "category": "テストカテゴリ",
                "features": {
                    "color": "テスト色",
                    "cut_technique": "テストカット",
                    "styling": "テストスタイリング",
                    "impression": "テスト印象"
                },
                "keywords": ["キーワード1", "キーワード2"]
            }
            response_mock = MagicMock(text=json.dumps(response_json))
            future = asyncio.Future()
            future.set_result(response_mock)
            mock_loop.run_in_executor.return_value = future
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # 画像分析
                categories = ["カテゴリ1", "カテゴリ2"]
                result = self.run_async(self.service.analyze_image(self.temp_image, categories))
                
                # 結果を確認
                self.assertEqual(result.category, "テストカテゴリ")
                self.assertEqual(result.features.color, "テスト色")
                self.assertEqual(result.features.cut_technique, "テストカット")
                self.assertEqual(result.features.styling, "テストスタイリング")
                self.assertEqual(result.features.impression, "テスト印象")
                self.assertEqual(result.keywords, ["キーワード1", "キーワード2"])
    
    def test_analyze_attributes(self):
        """属性分析テスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # API呼び出しの結果をモック
            response_json = {
                "sex": "レディース",
                "length": "ロング"
            }
            response_mock = MagicMock(text=json.dumps(response_json))
            future = asyncio.Future()
            future.set_result(response_mock)
            mock_loop.run_in_executor.return_value = future
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # 属性分析
                result = self.run_async(self.service.analyze_attributes(self.temp_image))
                
                # 結果を確認
                self.assertEqual(result.sex, "レディース")
                self.assertEqual(result.length, "ロング")
    
    def test_select_stylist(self):
        """スタイリスト選択テスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # API呼び出しの結果をモック
            response_json = {
                "stylist_name": "テストスタイリスト2"
            }
            response_mock = MagicMock(text=json.dumps(response_json))
            future = asyncio.Future()
            future.set_result(response_mock)
            mock_loop.run_in_executor.return_value = future
            
            # スタイリストのリスト
            stylists = [
                StylistInfo(name="テストスタイリスト1", description="説明1"),
                StylistInfo(name="テストスタイリスト2", description="説明2", position="役職2"),
                StylistInfo(name="テストスタイリスト3", description="説明3")
            ]
            
            # 分析結果
            features = StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            )
            analysis = StyleAnalysis(
                category="テストカテゴリ",
                features=features,
                keywords=["キーワード1", "キーワード2"]
            )
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # スタイリスト選択
                result = self.run_async(self.service.select_stylist(self.temp_image, stylists, analysis))
                
                # 結果を確認
                self.assertEqual(result.name, "テストスタイリスト2")
                self.assertEqual(result.description, "説明2")
                self.assertEqual(result.position, "役職2")
    
    def test_select_coupon(self):
        """クーポン選択テスト"""
        # モックのセットアップ
        with patch('hairstyle_analyzer.services.gemini.gemini_service.asyncio.get_event_loop') as mock_get_loop:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop
            
            # API呼び出しの結果をモック
            response_json = {
                "coupon_name": "テストクーポン1"
            }
            response_mock = MagicMock(text=json.dumps(response_json))
            future = asyncio.Future()
            future.set_result(response_mock)
            mock_loop.run_in_executor.return_value = future
            
            # クーポンのリスト
            coupons = [
                CouponInfo(name="テストクーポン1", price="1000円"),
                CouponInfo(name="テストクーポン2"),
                CouponInfo(name="テストクーポン3", price="3000円")
            ]
            
            # 分析結果
            features = StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            )
            analysis = StyleAnalysis(
                category="テストカテゴリ",
                features=features,
                keywords=["キーワード1", "キーワード2"]
            )
            
            # 画像準備のモック
            with patch.object(self.service, '_prepare_image', return_value={"mime_type": "image/jpeg", "data": "encoded_data"}):
                # クーポン選択
                result = self.run_async(self.service.select_coupon(self.temp_image, coupons, analysis))
                
                # 結果を確認
                self.assertEqual(result.name, "テストクーポン1")
                self.assertEqual(result.price, "1000円")


if __name__ == '__main__':
    unittest.main()
