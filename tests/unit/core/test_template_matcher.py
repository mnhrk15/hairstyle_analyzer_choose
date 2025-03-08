"""
TemplateMatcherのユニットテスト
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.data.models import Template, StyleAnalysis, StyleFeatures, GeminiConfig, TemplateMatchingConfig
from hairstyle_analyzer.utils.errors import TemplateError
from hairstyle_analyzer.services.gemini.gemini_service import GeminiService


@pytest.fixture
def mock_template_manager():
    """TemplateManagerのモック"""
    mock_manager = MagicMock()
    
    # サンプルテンプレート
    templates = [
        Template(
            category="テストカテゴリ1",
            title="テストタイトル1",
            menu="テストメニュー1",
            comment="テストコメント1",
            hashtag="テストタグ1,キーワード1"
        ),
        Template(
            category="テストカテゴリ2",
            title="テストタイトル2",
            menu="テストメニュー2",
            comment="テストコメント2",
            hashtag="テストタグ2,キーワード2"
        )
    ]
    
    # get_templates_by_category メソッドのモック
    def mock_get_templates_by_category(category):
        return [t for t in templates if t.category == category]
    
    mock_manager.get_templates_by_category.side_effect = mock_get_templates_by_category
    
    # get_all_categories メソッドのモック
    mock_manager.get_all_categories.return_value = ["テストカテゴリ1", "テストカテゴリ2"]
    
    # get_all_templates メソッドのモック
    mock_manager.get_all_templates.return_value = templates
    
    # find_best_template メソッドのモック
    def mock_find_best_template(analysis):
        for t in templates:
            if t.category == analysis.category:
                return t
        return templates[0] if templates else None
    
    mock_manager.find_best_template.side_effect = mock_find_best_template
    
    return mock_manager


@pytest.fixture
def template_matcher(mock_template_manager):
    """テスト対象のTemplateMatcherインスタンス"""
    return TemplateMatcher(mock_template_manager)


def test_find_best_template(template_matcher, mock_template_manager):
    """find_best_templateメソッドのテスト"""
    # テスト用の分析結果
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # テンプレート検索を実行
    result = template_matcher.find_best_template(analysis)
    
    # テンプレートマネージャーが正しく呼ばれたことを確認
    mock_template_manager.find_best_template.assert_called_once_with(analysis)
    
    # 結果が正しいことを確認
    assert result.category == "テストカテゴリ1"
    assert result.title == "テストタイトル1"
    assert result.menu == "テストメニュー1"
    assert result.comment == "テストコメント1"
    assert "テストタグ1" in result.hashtag


def test_find_alternative_templates(template_matcher):
    """find_alternative_templatesメソッドのテスト"""
    # テスト用の分析結果
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # 代替テンプレート検索を実行
    results = template_matcher.find_alternative_templates(analysis, count=2)
    
    # 結果の数が正しいことを確認
    assert len(results) <= 2
    
    # カテゴリに一致するテンプレートが取得されていることを確認
    category_templates = [t for t in results if t.category == "テストカテゴリ1"]
    assert len(category_templates) > 0


def test_find_alternative_templates_no_match(template_matcher, mock_template_manager):
    """カテゴリに一致するテンプレートがない場合のテスト"""
    # カテゴリに一致するテンプレートがない分析結果
    analysis = StyleAnalysis(
        category="存在しないカテゴリ",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # get_templates_by_category が空リストを返すように設定
    mock_template_manager.get_templates_by_category.return_value = []
    
    # 代替テンプレート検索を実行
    results = template_matcher.find_alternative_templates(analysis, count=2)
    
    # 全テンプレートから選択されていることを確認
    mock_template_manager.get_all_templates.assert_called_once()
    assert len(results) <= 2


def test_get_template_by_category(template_matcher, mock_template_manager):
    """get_template_by_categoryメソッドのテスト"""
    # 存在するカテゴリ
    result = template_matcher.get_template_by_category("テストカテゴリ1")
    
    # テンプレートマネージャーが正しく呼ばれたことを確認
    mock_template_manager.get_templates_by_category.assert_called_with("テストカテゴリ1")
    
    # 結果が正しいことを確認
    assert result.category == "テストカテゴリ1"
    assert result.title == "テストタイトル1"
    
    # 存在しないカテゴリ
    mock_template_manager.get_templates_by_category.return_value = []
    result = template_matcher.get_template_by_category("存在しないカテゴリ")
    
    # 結果がNoneであることを確認
    assert result is None


def test_get_random_template(template_matcher, mock_template_manager):
    """get_random_templateメソッドのテスト"""
    # ランダムテンプレートを取得
    result = template_matcher.get_random_template()
    
    # テンプレートマネージャーが正しく呼ばれたことを確認
    mock_template_manager.get_all_templates.assert_called_once()
    
    # 結果が正しいことを確認
    assert result is not None
    assert result.category in ["テストカテゴリ1", "テストカテゴリ2"]
    
    # テンプレートが存在しない場合
    mock_template_manager.get_all_templates.return_value = []
    result = template_matcher.get_random_template()
    
    # 結果がNoneであることを確認
    assert result is None


def test_score_templates(template_matcher):
    """_score_templatesメソッドのテスト"""
    # テスト用のテンプレートと分析結果
    templates = [
        Template(
            category="テストカテゴリ1",
            title="テストタイトル1",
            menu="テストメニュー1 テスト色",  # 特徴語を含む
            comment="テストコメント1",
            hashtag="テストタグ1,キーワード1"  # 分析結果のキーワードを含む
        ),
        Template(
            category="テストカテゴリ2",
            title="テストタイトル2",
            menu="テストメニュー2",
            comment="テストコメント2",
            hashtag="テストタグ2,キーワード2"
        )
    ]
    
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # スコアリングを実行
    scored_templates = template_matcher._score_templates(templates, analysis)
    
    # スコア付きテンプレートのリストが返されたことを確認
    assert len(scored_templates) == 2
    
    # 各要素がスコアとテンプレートのタプルであることを確認
    assert isinstance(scored_templates[0][0], float)  # スコア
    assert isinstance(scored_templates[0][1], Template)  # テンプレート
    
    # カテゴリが一致するテンプレートが高いスコアを持つことを確認
    assert scored_templates[0][1].category == "テストカテゴリ1"
    assert scored_templates[0][0] > scored_templates[1][0]


@pytest.fixture
def mock_gemini_service():
    """GeminiServiceのモック"""
    # GeminiConfigのモック
    template_matching_config = TemplateMatchingConfig(
        enabled=True,
        max_templates=50,
        use_category_filter=True,
        fallback_on_failure=True,
        cache_results=True,
        timeout_seconds=30
    )
    
    config = MagicMock()
    config.template_matching = template_matching_config
    
    # GeminiServiceのモック
    mock_service = AsyncMock()
    mock_service.config = config
    
    # select_best_templateメソッドのモック
    async def mock_select_best_template(image_path, templates, analysis=None, category_filter=False):
        # 成功時は最初のテンプレートのインデックスと理由を返す
        return 0, "AIによる選択理由"
    
    mock_service.select_best_template.side_effect = mock_select_best_template
    
    return mock_service


@pytest.mark.asyncio
async def test_find_best_template_with_ai(template_matcher, mock_gemini_service):
    """find_best_template_with_aiメソッドのテスト"""
    # テスト用の分析結果
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # テスト用の画像パス
    image_path = Path("dummy.jpg")
    
    # AIによるテンプレート選択を実行
    template, reason, success = await template_matcher.find_best_template_with_ai(
        image_path=image_path,
        gemini_service=mock_gemini_service,
        analysis=analysis,
        use_category_filter=True,
        max_templates=10
    )
    
    # GeminiServiceが正しく呼ばれたことを確認
    mock_gemini_service.select_best_template.assert_called_once()
    
    # 結果が正しいことを確認
    assert template is not None
    assert template.category == "テストカテゴリ1"
    assert template.title == "テストタイトル1"
    assert reason == "AIによる選択理由"
    assert success is True


@pytest.mark.asyncio
async def test_find_best_template_with_ai_failure(template_matcher, mock_gemini_service):
    """find_best_template_with_aiメソッドの失敗時のテスト"""
    # テスト用の分析結果
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # テスト用の画像パス
    image_path = Path("dummy.jpg")
    
    # GeminiServiceのselect_best_templateメソッドが失敗するようにモック
    mock_gemini_service.select_best_template.side_effect = Exception("テストエラー")
    
    # AIによるテンプレート選択を実行
    template, reason, success = await template_matcher.find_best_template_with_ai(
        image_path=image_path,
        gemini_service=mock_gemini_service,
        analysis=analysis,
        use_category_filter=True,
        max_templates=10
    )
    
    # 結果が正しいことを確認
    assert template is None
    assert "エラー" in reason
    assert success is False


@pytest.mark.asyncio
async def test_find_best_template_with_ai_no_templates(template_matcher, mock_gemini_service, mock_template_manager):
    """find_best_template_with_aiメソッドのテンプレートがない場合のテスト"""
    # テスト用の分析結果
    analysis = StyleAnalysis(
        category="テストカテゴリ1",
        features=StyleFeatures(
            color="テスト色",
            cut_technique="テストカット",
            styling="テストスタイリング",
            impression="テスト印象"
        ),
        keywords=["キーワード1", "テスト"]
    )
    
    # テスト用の画像パス
    image_path = Path("dummy.jpg")
    
    # テンプレートマネージャーが空のリストを返すようにモック
    mock_template_manager.get_templates_by_category.return_value = []
    mock_template_manager.get_all_templates.return_value = []
    
    # AIによるテンプレート選択を実行
    template, reason, success = await template_matcher.find_best_template_with_ai(
        image_path=image_path,
        gemini_service=mock_gemini_service,
        analysis=analysis,
        use_category_filter=True,
        max_templates=10
    )
    
    # 結果が正しいことを確認
    assert template is None
    assert "見つかりません" in reason
    assert success is False


def test_sample_templates(template_matcher, mock_template_manager):
    """_sample_templatesメソッドのテスト"""
    # テスト用のテンプレート
    templates = [
        Template(
            category="カテゴリA",
            title=f"タイトルA{i}",
            menu=f"メニューA{i}",
            comment=f"コメントA{i}",
            hashtag=f"タグA{i}"
        )
        for i in range(10)
    ] + [
        Template(
            category="カテゴリB",
            title=f"タイトルB{i}",
            menu=f"メニューB{i}",
            comment=f"コメントB{i}",
            hashtag=f"タグB{i}"
        )
        for i in range(10)
    ]
    
    # テンプレート数が上限以下の場合
    result = template_matcher._sample_templates(templates[:5], 10)
    assert len(result) == 5  # 全てのテンプレートが返される
    
    # テンプレート数が上限を超える場合
    result = template_matcher._sample_templates(templates, 10)
    assert len(result) == 10  # 上限数のテンプレートが返される
    
    # カテゴリごとのサンプリングが行われていることを確認
    categories = set(t.category for t in result)
    assert len(categories) <= 2  # 最大2つのカテゴリ
    
    # 極端に多いカテゴリ数の場合（ランダムサンプリングが使用される）
    many_categories = [
        Template(
            category=f"カテゴリ{i}",
            title=f"タイトル{i}",
            menu=f"メニュー{i}",
            comment=f"コメント{i}",
            hashtag=f"タグ{i}"
        )
        for i in range(30)
    ]
    
    result = template_matcher._sample_templates(many_categories, 10)
    assert len(result) == 10  # 上限数のテンプレートが返される
