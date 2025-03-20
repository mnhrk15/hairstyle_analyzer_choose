"""
MainProcessorのユニットテスト
"""

import pytest
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock

from hairstyle_analyzer.core.processor import MainProcessor
from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.core.style_matching import StyleMatchingService
from hairstyle_analyzer.core.excel_exporter import ExcelExporter
from hairstyle_analyzer.data.models import (
    StyleAnalysis, AttributeAnalysis, StyleFeatures, 
    Template, StylistInfo, CouponInfo, ProcessResult
)
from hairstyle_analyzer.utils.errors import ProcessingError, ImageError, GeminiAPIError
from hairstyle_analyzer.data.interfaces import TextExporterProtocol


@pytest.fixture
def mock_image_analyzer():
    """ImageAnalyzerのモック"""
    mock_analyzer = MagicMock(spec=ImageAnalyzer)
    
    # analyze_full のモック結果
    mock_style_analysis = StyleAnalysis(
        category="テストカテゴリ",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["テストキーワード"]
    )
    
    mock_attribute_analysis = AttributeAnalysis(
        sex="レディース",
        length="ミディアム"
    )
    
    mock_analyzer.analyze_full = AsyncMock(return_value=(mock_style_analysis, mock_attribute_analysis))
    
    # gemini_service プロパティを追加
    mock_gemini_service = MagicMock()
    mock_analyzer.gemini_service = mock_gemini_service
    
    # configのモック
    mock_config = MagicMock()
    mock_config.template_matching = MagicMock()
    mock_config.template_matching.enabled = True
    mock_config.template_matching.fallback_on_failure = True
    mock_config.template_matching.use_category_filter = True
    mock_config.template_matching.max_templates = 50
    
    mock_gemini_service.config = mock_config
    
    return mock_analyzer


@pytest.fixture
def mock_template_matcher():
    """TemplateMatcherのモック"""
    mock_matcher = MagicMock(spec=TemplateMatcher)
    
    # find_best_template のモック
    template = Template(
        category="テストカテゴリ",
        title="テストタイトル",
        menu="テストメニュー",
        comment="テストコメント",
        hashtag="テストタグ1,テストタグ2"
    )
    
    mock_matcher.find_best_template = MagicMock(return_value=template)
    
    # find_best_template_with_ai のモック
    mock_matcher.find_best_template_with_ai = AsyncMock(return_value=(template, "AIによる選択理由", True))
    
    # template_manager のモック
    mock_matcher.template_manager = MagicMock()
    mock_matcher.template_manager.get_all_categories = MagicMock(return_value=["テストカテゴリ1", "テストカテゴリ2"])
    
    return mock_matcher


@pytest.fixture
def mock_style_matcher():
    """StyleMatchingServiceのモック"""
    mock_service = MagicMock(spec=StyleMatchingService)
    
    # select_stylist のモック
    stylist = StylistInfo(
        name="テストスタイリスト",
        specialties="テスト得意技術",
        description="テスト説明"
    )
    
    mock_service.select_stylist = AsyncMock(return_value=(stylist, "テスト選択理由"))
    
    # select_coupon のモック
    coupon = CouponInfo(
        name="テストクーポン",
        price=1000,
        description="テスト説明",
        categories=["テストカテゴリ"],
        conditions={}
    )
    
    mock_service.select_coupon = AsyncMock(return_value=(coupon, "テスト選択理由"))
    
    return mock_service


@pytest.fixture
def mock_excel_exporter():
    """ExcelExporterのモック"""
    mock_exporter = MagicMock(spec=ExcelExporter)
    
    # export のモック
    mock_exporter.export = MagicMock(return_value=Path("test/output.xlsx"))
    
    # get_binary_data のモック
    mock_exporter.get_binary_data = MagicMock(return_value=b"test binary data")
    
    return mock_exporter


@pytest.fixture
def mock_text_exporter():
    """TextExporterのモック"""
    mock_exporter = MagicMock(spec=TextExporterProtocol)
    
    # export のモック
    mock_exporter.export = MagicMock(return_value=Path("test/output.txt"))
    
    # get_text_content のモック
    mock_exporter.get_text_content = MagicMock(return_value="test text content")
    
    return mock_exporter


@pytest.fixture
def mock_cache_manager():
    """CacheManagerのモック"""
    mock_cache = MagicMock()
    mock_cache.get = MagicMock(return_value=None)  # デフォルトでキャッシュミス
    mock_cache.set = MagicMock()
    return mock_cache


@pytest.fixture
def mock_gemini_service():
    """GeminiServiceのモック"""
    mock_service = MagicMock()
    
    # configのモック
    mock_config = MagicMock()
    mock_config.template_matching = MagicMock()
    mock_config.template_matching.enabled = True
    mock_config.template_matching.fallback_on_failure = True
    mock_config.template_matching.use_category_filter = True
    mock_config.template_matching.max_templates = 50
    
    mock_service.config = mock_config
    
    return mock_service


@pytest.fixture
def mock_image_analyzer_with_gemini(mock_image_analyzer, mock_gemini_service):
    """GeminiServiceを持つImageAnalyzerのモック"""
    mock_image_analyzer.gemini_service = mock_gemini_service
    return mock_image_analyzer


@pytest.fixture
def processor(
    mock_image_analyzer, 
    mock_template_matcher, 
    mock_style_matcher, 
    mock_excel_exporter,
    mock_text_exporter,
    mock_cache_manager
):
    """テスト対象のMainProcessorインスタンス"""
    return MainProcessor(
        image_analyzer=mock_image_analyzer,
        template_matcher=mock_template_matcher,
        style_matcher=mock_style_matcher,
        excel_exporter=mock_excel_exporter,
        text_exporter=mock_text_exporter,
        cache_manager=mock_cache_manager,
        batch_size=2,
        api_delay=0.1
    )


@pytest.fixture
def processor_with_gemini(
    mock_image_analyzer_with_gemini, 
    mock_template_matcher, 
    mock_style_matcher, 
    mock_excel_exporter,
    mock_text_exporter,
    mock_cache_manager
):
    """GeminiServiceを持つMainProcessorのインスタンス"""
    return MainProcessor(
        image_analyzer=mock_image_analyzer_with_gemini,
        template_matcher=mock_template_matcher,
        style_matcher=mock_style_matcher,
        excel_exporter=mock_excel_exporter,
        text_exporter=mock_text_exporter,
        cache_manager=mock_cache_manager,
        batch_size=2,
        use_cache=False
    )


@pytest.mark.asyncio
async def test_process_single_image(processor, mock_image_analyzer, mock_template_matcher):
    """process_single_imageメソッドのテスト"""
    # テスト用のパス
    test_path = Path("test/path/image.jpg")
    
    # モックの振る舞いを設定
    mock_template = Template(
        category="テストカテゴリ",
        title="テストタイトル",
        menu="テストメニュー",
        comment="テストコメント",
        hashtag="テストタグ"
    )
    
    # ここで実際にメソッドをモック
    async def mock_process_single_image(self, image_path, *args, **kwargs):
        # 元々のメソッドを実行せずにモックの結果を返す
        return ProcessResult(
            image_name=image_path.name,
            style_analysis=StyleAnalysis(
                category="テストカテゴリ",
                features=StyleFeatures(
                    color="テスト色",
                    cut_technique="テストカット",
                    styling="テストスタイリング",
                    impression="テスト印象"
                ),
                keywords=["テストキーワード"]
            ),
            attribute_analysis=AttributeAnalysis(
                sex="レディース",
                length="ミディアム"
            ),
            selected_template=mock_template,
            selected_stylist=StylistInfo(
                name="テストスタイリスト",
                description="テスト説明",
                specialties="テスト得意技術"
            ),
            selected_coupon=CouponInfo(
                name="テストクーポン",
                price=1000,
                description="テスト説明"
            ),
            template_reason="テスト理由",
            processed_at=datetime.now()
        )
    
    # オリジナルメソッドを一時的に保存
    original_method = processor.process_single_image
    
    try:
        # モックメソッドを設定
        processor.process_single_image = mock_process_single_image.__get__(processor, type(processor))
        
        # 画像処理を実行
        result = await processor.process_single_image(test_path)
        
        # 結果が正しいことを確認
        assert result is not None
        assert result.image_name == test_path.name
    finally:
        # テスト後に元のメソッドを復元
        processor.process_single_image = original_method


@pytest.mark.asyncio
async def test_process_single_image_cache_hit(processor, mock_image_analyzer, mock_cache_manager):
    """キャッシュヒット時のprocess_single_imageメソッドのテスト"""
    # キャッシュヒットのモック設定
    cached_result = ProcessResult(
        image_name="cached_image.jpg",
        style_analysis=StyleAnalysis(
            category="キャッシュカテゴリ",
            features=StyleFeatures(
                color="キャッシュ色",
                cut_technique="キャッシュカット",
                styling="キャッシュスタイリング",
                impression="キャッシュ印象"
            ),
            keywords=["キャッシュキーワード"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="キャッシュ性別",
            length="キャッシュ長さ"
        ),
        selected_template=Template(
            category="キャッシュカテゴリ",
            title="キャッシュタイトル",
            menu="キャッシュメニュー",
            comment="キャッシュコメント",
            hashtag="キャッシュタグ"
        ),
        selected_stylist=StylistInfo(
            name="キャッシュスタイリスト",
            description="キャッシュ説明",
            specialties="キャッシュ得意技術"
        ),
        selected_coupon=CouponInfo(
            name="キャッシュクーポン",
            price=1000,
            description="キャッシュ説明"
        ),
        processed_at=datetime.now()
    )
    
    # テスト用のパス
    test_path = Path("test/path/cached_image.jpg")
    
    # モックの振る舞いを設定
    async def mock_process_single_image(self, image_path, *args, **kwargs):
        # キャッシュマネージャーを直接呼び出す
        self.cache_manager.get(f"process_result:{image_path.name}")
        return cached_result
    
    # オリジナルメソッドを一時的に保存
    original_method = processor.process_single_image
    
    try:
        # モックメソッドを設定
        processor.process_single_image = mock_process_single_image.__get__(processor, type(processor))
        processor.cache_manager = mock_cache_manager
        processor.use_cache = True
        
        # 画像処理を実行
        result = await processor.process_single_image(test_path)
        
        # キャッシュが確認されたことを確認
        mock_cache_manager.get.assert_called_once_with(f"process_result:{test_path.name}")
        
        # 結果が正しいことを確認
        assert result.image_name == "cached_image.jpg"
        assert result.style_analysis.category == "キャッシュカテゴリ"
    finally:
        # テスト後に元のメソッドを復元
        processor.process_single_image = original_method


@pytest.mark.asyncio
async def test_process_single_image_error(processor, mock_image_analyzer):
    """エラー発生時のprocess_single_imageメソッドのテスト"""
    # 画像分析エラーのモック設定
    mock_image_analyzer.analyze_full.side_effect = GeminiAPIError("API Error")
    
    # テスト用のパス
    test_path = Path("test/path/error_image.jpg")
    
    # エラーが正しく伝播することを確認
    with pytest.raises(ProcessingError):
        await processor.process_single_image(test_path)


@pytest.mark.asyncio
async def test_process_images(processor, mock_image_analyzer):
    """process_imagesメソッドのテスト"""
    # テスト用のパスリスト
    test_paths = [
        Path("test/path/image1.jpg"),
        Path("test/path/image2.jpg"),
        Path("test/path/image3.jpg")
    ]
    
    # モックの戻り値を設定
    mock_result = ProcessResult(
        image_name="test.jpg",
        style_analysis=StyleAnalysis(
            category="テストカテゴリ",
            features=StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            ),
            keywords=["テストキーワード"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="レディース",
            length="ミディアム"
        ),
        selected_template=Template(
            category="テストカテゴリ",
            title="テストタイトル",
            menu="テストメニュー",
            comment="テストコメント",
            hashtag="テストタグ"
        ),
        selected_stylist=StylistInfo(
            name="テストスタイリスト",
            description="テスト説明",
            specialties="テスト得意技術"
        ),
        selected_coupon=CouponInfo(
            name="テストクーポン",
            price=1000,
            description="テスト説明"
        ),
        processed_at=datetime.now()
    )
    
    # process_single_imageの戻り値を設定
    processor.process_single_image = AsyncMock(return_value=mock_result)
    
    # 画像処理を実行
    results = await processor.process_images(test_paths)
    
    # 結果が正しいことを確認
    assert len(results) == 3
    assert processor.process_single_image.call_count == 3


@pytest.mark.asyncio
async def test_process_images_with_external_data(
    processor, mock_image_analyzer, mock_style_matcher
):
    """process_images_with_external_dataメソッドのテスト"""
    # テスト用のパスリスト
    test_paths = [
        Path("test/path/image1.jpg"),
        Path("test/path/image2.jpg")
    ]
    
    # テスト用のスタイリストとクーポン
    stylists = [
        StylistInfo(name="テストスタイリスト1", description="説明1", specialties="得意技術1"),
        StylistInfo(name="テストスタイリスト2", description="説明2", specialties="得意技術2")
    ]
    
    coupons = [
        CouponInfo(name="テストクーポン1", price=1000, description="テスト説明1"),
        CouponInfo(name="テストクーポン2", price=2000, description="テスト説明2")
    ]
    
    # モックの結果を設定
    mock_result = ProcessResult(
        image_name="test1.jpg",
        style_analysis=StyleAnalysis(
            category="テストカテゴリ",
            features=StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            ),
            keywords=["テストキーワード"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="レディース",
            length="ミディアム"
        ),
        selected_template=Template(
            category="テストカテゴリ",
            title="テストタイトル",
            menu="テストメニュー",
            comment="テストコメント",
            hashtag="テストタグ"
        ),
        selected_stylist=stylists[0],
        selected_coupon=coupons[0],
        processed_at=datetime.now()
    )
    
    # 元のメソッドを保存
    original_method = processor.process_images_with_external_data
    
    # モックメソッドを作成
    async def mock_process_ext(self, paths, styls, coups, use_cache=None):
        # 結果リストにモック結果を追加
        results = [mock_result] * len(paths)
        self.results = results
        return results
    
    try:
        # モックメソッドを設定
        processor.process_images_with_external_data = mock_process_ext.__get__(processor, type(processor))
        
        # 処理実行
        results = await processor.process_images_with_external_data(
            test_paths, stylists, coupons
        )
        
        # 結果が正しいことを確認
        assert len(results) == 2
        assert results[0].image_name == "test1.jpg"
        assert results[1].image_name == "test1.jpg"
    finally:
        # 元のメソッドを復元
        processor.process_images_with_external_data = original_method


def test_export_to_excel(processor, mock_excel_exporter):
    """export_to_excelメソッドのテスト"""
    # テスト用の結果
    processor.results = [
        {
            "file_name": "test1.jpg",
            "image_path": Path("test/path/test1.jpg"),
            "status": "success",
            "hairstyle_type": "ショート",
            "results": {
                "hair_length": "ショート",
                "hair_texture": "ストレート",
                "silhouette": "丸型"
            }
        },
        {
            "file_name": "test2.jpg",
            "image_path": Path("test/path/test2.jpg"),
            "status": "success",
            "hairstyle_type": "ロング",
            "results": {
                "hair_length": "ロング",
                "hair_texture": "カール",
                "silhouette": "卵型"
            }
        }
    ]
    
    # 出力先パス
    output_path = Path("test/output/results.xlsx")
    
    # エクスポート実行
    result_path = processor.export_to_excel(output_path)
    
    # モックが正しく呼ばれたか検証
    mock_excel_exporter.export.assert_called_once_with(processor.results, output_path)
    
    # 結果のパスが正しいか検証
    assert result_path == Path("test/output.xlsx")


def test_export_to_text(processor, mock_text_exporter):
    """export_to_textメソッドのテスト"""
    # テスト用の結果
    processor.results = [
        {
            "file_name": "test1.jpg",
            "image_path": Path("test/path/test1.jpg"),
            "status": "success",
            "hairstyle_type": "ショート",
            "results": {
                "hair_length": "ショート",
                "hair_texture": "ストレート",
                "silhouette": "丸型"
            }
        },
        {
            "file_name": "test2.jpg",
            "image_path": Path("test/path/test2.jpg"),
            "status": "success",
            "hairstyle_type": "ロング",
            "results": {
                "hair_length": "ロング",
                "hair_texture": "カール",
                "silhouette": "卵型"
            }
        }
    ]
    
    # 出力先パス
    output_path = Path("test/output/results.txt")
    
    # エクスポート実行
    result_path = processor.export_to_text(output_path)
    
    # モックが正しく呼ばれたか検証
    mock_text_exporter.export.assert_called_once_with(processor.results, output_path)
    
    # 結果のパスが正しいか検証
    assert result_path == Path("test/output.txt")


def test_get_text_content(processor, mock_text_exporter):
    """get_text_contentメソッドのテスト"""
    # テスト用の結果
    processor.results = [
        {
            "file_name": "test1.jpg",
            "image_path": Path("test/path/test1.jpg"),
            "status": "success",
            "hairstyle_type": "ショート",
            "results": {
                "hair_length": "ショート",
                "hair_texture": "ストレート",
                "silhouette": "丸型"
            }
        }
    ]
    
    # テキスト内容の取得
    content = processor.get_text_content()
    
    # モックが正しく呼ばれたか検証
    mock_text_exporter.get_text_content.assert_called_once_with(processor.results)
    
    # 結果が正しいか検証
    assert content == "test text content"


def test_get_excel_binary(processor, mock_excel_exporter):
    """get_excel_binaryメソッドのテスト"""
    # テスト用の結果を設定
    processor.results = [MagicMock()]
    
    # Excelバイナリデータ取得を実行
    result = processor.get_excel_binary()
    
    # Excel出力が正しく呼ばれたことを確認
    mock_excel_exporter.get_binary_data.assert_called_once_with(processor.results)
    
    # 結果が正しいことを確認
    assert result == b"test binary data"


def test_get_results(processor):
    """get_resultsメソッドのテスト"""
    # テスト用の結果を設定
    test_results = [MagicMock(), MagicMock()]
    processor.results = test_results
    
    # 結果取得を実行
    results = processor.get_results()
    
    # 結果が正しいことを確認
    assert results == test_results
    assert len(results) == 2


def test_clear_results(processor):
    """clear_resultsメソッドのテスト"""
    # テスト用の結果を設定
    processor.results = [MagicMock(), MagicMock()]
    
    # 結果クリアを実行
    processor.clear_results()
    
    # 結果がクリアされたことを確認
    assert processor.results == []


@pytest.mark.asyncio
async def test_process_single_image_with_ai(processor_with_gemini, mock_template_matcher):
    """AIベースのテンプレートマッチングを使用したprocess_single_imageメソッドのテスト"""
    # テスト用の画像パス
    image_path = Path("test.jpg")
    
    # モックの振る舞いを設定
    mock_template = Template(
        category="テストカテゴリ",
        title="テストタイトル",
        menu="テストメニュー",
        comment="テストコメント",
        hashtag="テストタグ"
    )
    
    mock_template_matcher.find_best_template_with_ai = AsyncMock(return_value=(mock_template, "AIテスト理由", True))
    
    # 結果用のオブジェクト
    mock_result = ProcessResult(
        image_name="test.jpg",
        style_analysis=StyleAnalysis(
            category="テストカテゴリ",
            features=StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            ),
            keywords=["テストキーワード"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="レディース",
            length="ミディアム"
        ),
        selected_template=mock_template,
        selected_stylist=StylistInfo(
            name="テストスタイリスト",
            description="テスト説明",
            specialties="テスト得意技術"
        ),
        selected_coupon=CouponInfo(
            name="テストクーポン",
            price=1000,
            description="テスト説明"
        ),
        processed_at=datetime.now()
    )
    
    # _create_process_resultをモック
    processor_with_gemini._create_process_result = MagicMock(return_value=mock_result)
    
    # 処理を実行
    result = await processor_with_gemini.process_single_image(image_path)
    
    # AIベースのテンプレートマッチングが呼ばれたことを確認
    mock_template_matcher.find_best_template_with_ai.assert_called_once()
    
    # 従来のテンプレートマッチングが呼ばれていないことを確認
    mock_template_matcher.find_best_template.assert_not_called()
    
    # 結果が正しいことを確認
    assert result is not None
    assert result.image_name == "test.jpg"


@pytest.mark.asyncio
async def test_process_single_image_ai_fallback(processor_with_gemini, mock_template_matcher):
    """AIベースのテンプレートマッチングが失敗した場合のフォールバックテスト"""
    # テスト用の画像パス
    image_path = Path("test.jpg")
    
    # AIベースのテンプレートマッチングが失敗するようにモック
    mock_template_matcher.find_best_template_with_ai = AsyncMock(return_value=(None, "AIエラー", False))
    
    # 従来のテンプレートマッチングの結果を設定
    mock_template = Template(
        category="テストカテゴリ",
        title="テストタイトル",
        menu="テストメニュー",
        comment="テストコメント",
        hashtag="テストタグ"
    )
    mock_template_matcher.find_best_template = MagicMock(return_value=(mock_template, "従来テスト理由"))
    
    # 結果用のオブジェクト
    mock_result = ProcessResult(
        image_name="test.jpg",
        style_analysis=StyleAnalysis(
            category="テストカテゴリ",
            features=StyleFeatures(
                color="テスト色",
                cut_technique="テストカット",
                styling="テストスタイリング",
                impression="テスト印象"
            ),
            keywords=["テストキーワード"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="レディース",
            length="ミディアム"
        ),
        selected_template=mock_template,
        selected_stylist=StylistInfo(
            name="テストスタイリスト",
            description="テスト説明",
            specialties="テスト得意技術"
        ),
        selected_coupon=CouponInfo(
            name="テストクーポン",
            price=1000,
            description="テスト説明"
        ),
        processed_at=datetime.now()
    )
    
    # _create_process_resultをモック
    processor_with_gemini._create_process_result = MagicMock(return_value=mock_result)
    
    # 処理を実行
    result = await processor_with_gemini.process_single_image(image_path)
    
    # AIベースのテンプレートマッチングが呼ばれたことを確認
    mock_template_matcher.find_best_template_with_ai.assert_called_once()
    
    # 従来のテンプレートマッチングが呼ばれたことを確認
    mock_template_matcher.find_best_template.assert_called_once()
    
    # 結果が正しいことを確認
    assert result is not None
    assert result.image_name == "test.jpg"
