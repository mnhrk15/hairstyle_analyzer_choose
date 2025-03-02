"""
ImageAnalyzerのユニットテスト
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.services.gemini import GeminiService
from hairstyle_analyzer.data.models import StyleAnalysis, AttributeAnalysis, StyleFeatures


@pytest.fixture
def mock_gemini_service():
    """GeminiServiceのモック"""
    mock_service = MagicMock(spec=GeminiService)
    
    # analyze_imageのモック
    mock_style_analysis = StyleAnalysis(
        category="テストカテゴリ",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["テストキーワード1", "テストキーワード2"]
    )
    mock_service.analyze_image = AsyncMock(return_value=mock_style_analysis)
    
    # analyze_attributesのモック
    mock_attribute_analysis = AttributeAnalysis(
        sex="レディース",
        length="ミディアム"
    )
    mock_service.analyze_attributes = AsyncMock(return_value=mock_attribute_analysis)
    
    return mock_service


@pytest.fixture
def mock_cache_manager():
    """CacheManagerのモック"""
    mock_cache = MagicMock()
    mock_cache.get = MagicMock(return_value=None)  # デフォルトでキャッシュミス
    mock_cache.set = MagicMock()
    return mock_cache


@pytest.fixture
def image_analyzer(mock_gemini_service, mock_cache_manager):
    """テスト対象のImageAnalyzerインスタンス"""
    return ImageAnalyzer(mock_gemini_service, mock_cache_manager)


@pytest.mark.asyncio
async def test_analyze_image(image_analyzer, mock_gemini_service):
    """analyze_imageメソッドのテスト"""
    # テスト用のパスとカテゴリ
    test_path = Path("test/path/image.jpg")
    test_categories = ["カテゴリ1", "カテゴリ2"]
    
    # 画像分析を実行
    result = await image_analyzer.analyze_image(test_path, test_categories)
    
    # Gemini APIが正しく呼ばれたことを確認
    mock_gemini_service.analyze_image.assert_awaited_once_with(test_path, test_categories)
    
    # 結果が正しいことを確認
    assert result.category == "テストカテゴリ"
    assert result.features.color == "テスト色"
    assert result.features.cut_technique == "テストカット"
    assert result.features.styling == "テストスタイリング"
    assert result.features.impression == "テスト印象"
    assert "テストキーワード1" in result.keywords
    assert "テストキーワード2" in result.keywords


@pytest.mark.asyncio
async def test_analyze_attributes(image_analyzer, mock_gemini_service):
    """analyze_attributesメソッドのテスト"""
    # テスト用のパス
    test_path = Path("test/path/image.jpg")
    
    # 属性分析を実行
    result = await image_analyzer.analyze_attributes(test_path)
    
    # Gemini APIが正しく呼ばれたことを確認
    mock_gemini_service.analyze_attributes.assert_awaited_once_with(test_path)
    
    # 結果が正しいことを確認
    assert result.sex == "レディース"
    assert result.length == "ミディアム"


@pytest.mark.asyncio
async def test_analyze_full(image_analyzer):
    """analyze_fullメソッドのテスト"""
    # テスト用のパスとカテゴリ
    test_path = Path("test/path/image.jpg")
    test_categories = ["カテゴリ1", "カテゴリ2"]
    
    # 完全分析を実行
    style_analysis, attribute_analysis = await image_analyzer.analyze_full(test_path, test_categories)
    
    # 結果が正しいことを確認
    assert style_analysis.category == "テストカテゴリ"
    assert style_analysis.features.color == "テスト色"
    assert style_analysis.features.cut_technique == "テストカット"
    assert style_analysis.features.styling == "テストスタイリング"
    assert style_analysis.features.impression == "テスト印象"
    assert "テストキーワード1" in style_analysis.keywords
    assert "テストキーワード2" in style_analysis.keywords
    
    assert attribute_analysis.sex == "レディース"
    assert attribute_analysis.length == "ミディアム"


@pytest.mark.asyncio
async def test_cache_hit(image_analyzer, mock_cache_manager):
    """キャッシュヒットのテスト"""
    # キャッシュヒットのモック設定
    mock_style_analysis = StyleAnalysis(
        category="キャッシュカテゴリ",
        features=StyleFeatures(
            color="キャッシュ色",
            cut_technique="キャッシュカット",
            styling="キャッシュスタイリング",
            impression="キャッシュ印象"
        ),
        keywords=["キャッシュキーワード"]
    )
    mock_cache_manager.get.return_value = mock_style_analysis
    
    # テスト用のパスとカテゴリ
    test_path = Path("test/path/cache_image.jpg")
    test_categories = ["カテゴリ1", "カテゴリ2"]
    
    # 画像分析を実行
    result = await image_analyzer.analyze_image(test_path, test_categories)
    
    # キャッシュが確認されたことを確認
    mock_cache_manager.get.assert_called_once_with(f"style_analysis:{test_path.name}")
    
    # Gemini APIが呼ばれなかったことを確認
    image_analyzer.gemini_service.analyze_image.assert_not_awaited()
    
    # 結果がキャッシュから取得されたことを確認
    assert result.category == "キャッシュカテゴリ"
    assert result.features.color == "キャッシュ色"
    assert "キャッシュキーワード" in result.keywords


@pytest.mark.asyncio
async def test_api_error(image_analyzer, mock_gemini_service):
    """API呼び出しエラーのテスト"""
    # API呼び出しエラーのモック設定
    from hairstyle_analyzer.utils.errors import GeminiAPIError
    mock_gemini_service.analyze_image.side_effect = GeminiAPIError("API Error")
    
    # テスト用のパスとカテゴリ
    test_path = Path("test/path/error_image.jpg")
    test_categories = ["カテゴリ1", "カテゴリ2"]
    
    # エラーが正しく伝播することを確認
    with pytest.raises(GeminiAPIError):
        await image_analyzer.analyze_image(test_path, test_categories)
