"""
TemplateManagerのユニットテスト
"""

import os
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock

import pandas as pd

from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.models import Template, StyleAnalysis, StyleFeatures
from hairstyle_analyzer.utils.errors import TemplateError


class TestTemplateManager(unittest.TestCase):
    """TemplateManagerのテストケース"""
    
    def setUp(self):
        """テストの前処理"""
        # テスト用CSVファイルを作成
        self.csv_content = """category,title,menu,comment,hashtag
最新トレンド,テスト透明感ボブ,カット+カラー,テストコメント,ハッシュタグ1
髪質改善,テストストレート,トリートメント,テストコメント2,ハッシュタグ2
ショート・ボブ,テストショート,カット,テストコメント3,ハッシュタグ3"""
        
        # 一時ファイルの作成
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_csv_path = Path(self.temp_dir.name) / "test_template.csv"
        
        with open(self.temp_csv_path, 'w', encoding='utf-8') as f:
            f.write(self.csv_content)
        
        # テスト対象のインスタンス作成
        self.template_manager = TemplateManager(self.temp_csv_path)
    
    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリの削除
        self.temp_dir.cleanup()
    
    def test_load_templates(self):
        """テンプレートの読み込みテスト"""
        # テンプレート数の確認
        self.assertEqual(len(self.template_manager.templates), 3)
        
        # カテゴリ数の確認
        self.assertEqual(len(self.template_manager.templates_by_category), 3)
        
        # 各カテゴリのテンプレート数の確認
        self.assertEqual(len(self.template_manager.templates_by_category['最新トレンド']), 1)
        self.assertEqual(len(self.template_manager.templates_by_category['髪質改善']), 1)
        self.assertEqual(len(self.template_manager.templates_by_category['ショート・ボブ']), 1)
    
    def test_validate_headers_valid(self):
        """有効なヘッダーの検証テスト"""
        # 有効なヘッダーの場合はエラーが発生しないことを確認
        valid_headers = ['category', 'title', 'menu', 'comment', 'hashtag', 'extra']
        self.template_manager._validate_headers(valid_headers)  # エラーが発生しないはず
    
    def test_validate_headers_invalid(self):
        """無効なヘッダーの検証テスト"""
        # 必須フィールドが不足している場合はTemplateErrorが発生することを確認
        invalid_headers = ['category', 'title', 'menu']  # commentとhashtagが不足
        
        with self.assertRaises(TemplateError) as cm:
            self.template_manager._validate_headers(invalid_headers)
        
        # エラーメッセージに不足フィールドが含まれていることを確認
        self.assertIn('comment', str(cm.exception))
        self.assertIn('hashtag', str(cm.exception))
    
    def test_get_templates_by_category(self):
        """カテゴリ別テンプレート取得テスト"""
        # 存在するカテゴリの場合
        templates = self.template_manager.get_templates_by_category('最新トレンド')
        self.assertEqual(len(templates), 1)
        self.assertEqual(templates[0].title, 'テスト透明感ボブ')
        
        # 存在しないカテゴリの場合は空リストが返ることを確認
        templates = self.template_manager.get_templates_by_category('存在しないカテゴリ')
        self.assertEqual(templates, [])
    
    def test_get_all_categories(self):
        """全カテゴリ取得テスト"""
        categories = self.template_manager.get_all_categories()
        self.assertEqual(len(categories), 3)
        self.assertIn('最新トレンド', categories)
        self.assertIn('髪質改善', categories)
        self.assertIn('ショート・ボブ', categories)
    
    def test_get_all_templates(self):
        """全テンプレート取得テスト"""
        templates = self.template_manager.get_all_templates()
        self.assertEqual(len(templates), 3)
        
        # コピーが返されることを確認（元のリストと異なるオブジェクト）
        self.assertIsNot(templates, self.template_manager.templates)
    
    def test_find_best_template_exact_category(self):
        """正確なカテゴリでの最適テンプレート検索テスト"""
        # テスト用の分析結果
        features = StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        )
        analysis = StyleAnalysis(
            category="最新トレンド",
            features=features,
            keywords=["ハッシュタグ1", "テスト"]
        )
        
        # 最適なテンプレートを取得
        template = self.template_manager.find_best_template(analysis)
        
        # テンプレートが見つかることを確認
        self.assertIsNotNone(template)
        self.assertEqual(template.category, "最新トレンド")
        self.assertEqual(template.title, "テスト透明感ボブ")
    
    def test_find_best_template_similar_category(self):
        """類似カテゴリでの最適テンプレート検索テスト"""
        # テスト用の分析結果（存在しないが類似したカテゴリ）
        features = StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        )
        analysis = StyleAnalysis(
            category="トレンド",  # 「最新トレンド」の一部のみ
            features=features,
            keywords=["ハッシュタグ1", "テスト"]
        )
        
        # 最適なテンプレートを取得
        template = self.template_manager.find_best_template(analysis)
        
        # テンプレートが見つかることを確認
        self.assertIsNotNone(template)
        # 最も近いカテゴリのテンプレートが返されることを確認
        self.assertEqual(template.category, "最新トレンド")
    
    def test_find_best_template_no_match(self):
        """該当するテンプレートがない場合のテスト"""
        # 空のテンプレートリストで初期化
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write("category,title,menu,comment,hashtag")
        
        try:
            empty_manager = TemplateManager(f.name)
            
            # テスト用の分析結果
            features = StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            )
            analysis = StyleAnalysis(
                category="最新トレンド",
                features=features,
                keywords=["ハッシュタグ1", "テスト"]
            )
            
            # 最適なテンプレートを取得
            template = empty_manager.find_best_template(analysis)
            
            # テンプレートが見つからないことを確認
            self.assertIsNone(template)
        finally:
            # 一時ファイルの削除
            os.unlink(f.name)
    
    def test_find_closest_category(self):
        """最も近いカテゴリ検索テスト"""
        # 「最新トレンド」に近い
        closest = self.template_manager._find_closest_category("最新")
        self.assertEqual(closest, "最新トレンド")
        
        # 「ショート・ボブ」に近い
        closest = self.template_manager._find_closest_category("ショート")
        self.assertEqual(closest, "ショート・ボブ")
        
        # まったく一致しない場合は最初のカテゴリが返る
        closest = self.template_manager._find_closest_category("まったく違うカテゴリ")
        self.assertIn(closest, self.template_manager.get_all_categories())
    
    def test_score_templates(self):
        """テンプレートスコアリングテスト"""
        # テスト用の分析結果
        features = StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        )
        analysis = StyleAnalysis(
            category="最新トレンド",
            features=features,
            keywords=["ハッシュタグ1", "テスト"]
        )
        
        # スコアリング
        scored_templates = self.template_manager._score_templates(
            self.template_manager.templates, analysis
        )
        
        # スコアリング結果の確認
        self.assertGreaterEqual(len(scored_templates), 1)
        
        # スコアと一緒にテンプレートが返されることを確認
        self.assertIsInstance(scored_templates[0][0], float)  # スコア
        self.assertIsInstance(scored_templates[0][1], Template)  # テンプレート
        
        # スコア順にソートされていることを確認
        for i in range(len(scored_templates) - 1):
            self.assertGreaterEqual(scored_templates[i][0], scored_templates[i+1][0])
    
    def test_reload(self):
        """テンプレート再読み込みテスト"""
        # 最初のテンプレート数を記録
        initial_count = len(self.template_manager.templates)
        
        # CSVファイルを更新（1行追加）
        with open(self.temp_csv_path, 'a', encoding='utf-8') as f:
            f.write("\nメンズ,テストメンズ,カット,テストコメント4,ハッシュタグ4")
        
        # 再読み込み
        self.template_manager.reload()
        
        # テンプレート数が増えていることを確認
        self.assertEqual(len(self.template_manager.templates), initial_count + 1)
        
        # 新しいカテゴリが追加されていることを確認
        self.assertIn('メンズ', self.template_manager.get_all_categories())


if __name__ == '__main__':
    unittest.main()
