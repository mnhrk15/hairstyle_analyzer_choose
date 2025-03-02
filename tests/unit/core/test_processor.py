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


@pytest.fixture
def mock_image_analyzer():
    """ImageAnalyzerのモック"""
    mock_analyzer = MagicMock(spec=ImageAnalyzer)
    
    # analyze_full のモック
    style_analysis = StyleAnalysis(
        category="テストカテゴリ",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["テストキーワード1", "テストキーワード2"]
    )
    
    attribute_analysis = AttributeAnalysis(
        sex="レディース",
        length="ミディアム"
    )
    
    mock_analyzer.analyze_full = AsyncMock(return_value=(style_analysis, attribute_analysis))
    
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
        description="テスト説明",
        position="テスト役職"
    )
    
    mock_service.select_stylist = AsyncMock(return_value=stylist)
    
    # select_coupon のモック
    coupon = CouponInfo(
        name="テストクーポン",
        price="1000円"
    )
    
    mock_service.select_coupon = AsyncMock(return_value=coupon)
    
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
def mock_cache_manager():
    """CacheManagerのモック"""
    mock_cache = MagicMock()
    mock_cache.get = MagicMock(return_value=None)  # デフォルトでキャッシュミス
    mock_cache.set = MagicMock()
    return mock_cache


@pytest.fixture
def processor(
    mock_image_analyzer, 
    mock_template_matcher, 
    mock_style_matcher, 
    mock_excel_exporter, 
    mock_cache_manager
):
    """テスト対象のMainProcessorインスタンス"""
    return MainProcessor(
        image_analyzer=mock_image_analyzer,
        template_matcher=mock_template_matcher,
        style_matcher=mock_style_matcher,
        excel_exporter=mock_excel_exporter,
        cache_manager=mock_cache_manager,
        batch_size=2,
        api_delay=0.1
    )


@pytest.mark.asyncio
async def test_process_single_image(processor, mock_image_analyzer, mock_template_matcher):
    """process_single_imageメソッドのテスト"""
    # テスト用のパス
    test_path = Path("test/path/image.jpg")
    
    # 画像処理を実行
    result = await processor.process_single_image(test_path)
    
    # 各コンポーネントが正しく呼ばれたことを確認
    mock_image_analyzer.analyze_full.assert_awaited_once()
    mock_template_matcher.find_best_template.assert_called_once()
    
    # 結果が正しいことを確認
    assert result.image_name == test_path.name
    assert result.style_analysis.category == "テストカテゴリ"
    assert result.attribute_analysis.sex == "レディース"
    assert result.selected_template.title == "テストタイトル"
    assert result.selected_stylist.name == "サンプルスタイリスト"  # デフォルト値
    assert result.selected_coupon.name == "サンプルクーポン"  # デフォルト値


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
            position="キャッシュ役職"
        ),
        selected_coupon=CouponInfo(
            name="キャッシュクーポン",
            price="キャッシュ価格"
        ),
        processed_at=datetime.now()
    )
    mock_cache_manager.get.return_value = cached_result
    
    # テスト用のパス
    test_path = Path("test/path/cached_image.jpg")
    
    # 画像処理を実行
    result = await processor.process_single_image(test_path)
    
    # キャッシュが確認されたことを確認
    mock_cache_manager.get.assert_called_once_with(f"process_result:{test_path.name}")
    
    # 画像分析が呼ばれないことを確認
    mock_image_analyzer.analyze_full.assert_not_awaited()
    
    # 結果がキャッシュから取得されたことを確認
    assert result.image_name == "cached_image.jpg"
    assert result.style_analysis.category == "キャッシュカテゴリ"
    assert result.attribute_analysis.sex == "キャッシュ性別"
    assert result.selected_template.title == "キャッシュタイトル"
    assert result.selected_stylist.name == "キャッシュスタイリスト"
    assert result.selected_coupon.name == "キャッシュクーポン"


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
    
    # 画像処理を実行
    results = await processor.process_images(test_paths)
    
    # 結果が正しいことを確認
    assert len(results) == 3
    assert all(isinstance(result, ProcessResult) for result in results)
    
    # 画像分析が正しい回数呼ばれたことを確認
    assert mock_image_analyzer.analyze_full.await_count == 3


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
        StylistInfo(name="テストスタイリスト1", description="説明1", position="役職1"),
        StylistInfo(name="テストスタイリスト2", description="説明2", position="役職2")
    ]
    
    coupons = [
        CouponInfo(name="テストクーポン1", price="1000円"),
        CouponInfo(name="テストクーポン2", price="2000円")
    ]
    
    # 外部データを使用した画像処理を実行
    results = await processor.process_images_with_external_data(test_paths, stylists, coupons)
    
    # 結果が正しいことを確認
    assert len(results) == 2
    assert all(isinstance(result, ProcessResult) for result in results)
    
    # スタイリストとクーポンの選択が呼ばれたことを確認
    assert mock_style_matcher.select_stylist.await_count == 2
    assert mock_style_matcher.select_coupon.await_count == 2


def test_export_to_excel(processor, mock_excel_exporter):
    """export_to_excelメソッドのテスト"""
    # テスト用の結果を設定
    processor.results = [
        ProcessResult(
            image_name="test_image.jpg",
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
                position="テスト役職"
            ),
            selected_coupon=CouponInfo(
                name="テストクーポン",
                price="テスト価格"
            ),
            processed_at=datetime.now()
        )
    ]
    
    # Excel出力を実行
    output_path = Path("test/output.xlsx")
    result_path = processor.export_to_excel(output_path)
    
    # Excel出力が正しく呼ばれたことを確認
    mock_excel_exporter.export.assert_called_once_with(processor.results, output_path)
    
    # 結果が正しいことを確認
    assert result_path == Path("test/output.xlsx")


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
