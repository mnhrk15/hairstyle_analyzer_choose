"""
TextExporterのユニットテスト
"""

import os
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

from hairstyle_analyzer.core.text_exporter import TextExporter, TextExportError
from hairstyle_analyzer.data.models import (
    TextConfig, ProcessResult, StyleAnalysis, StyleFeatures, 
    AttributeAnalysis, Template, StylistInfo, CouponInfo
)


@pytest.fixture
def text_config():
    """テキスト出力の設定"""
    return TextConfig(
        format_template="【画像名】{image_name}\n①スタイリスト名: {stylist_name}\n②コメント: {comment}\n"
                      "③スタイルタイトル: {title}\n④性別: {sex}\n⑤長さ: {length}\n"
                      "⑥スタイルメニュー: {menu}\n⑦クーポン名: {coupon_name}\n⑧ハッシュタグ: {hashtag}",
        encoding="utf-8",
        newline="\n"
    )


@pytest.fixture
def text_exporter(text_config):
    """テスト用のTextExporterインスタンス"""
    return TextExporter(text_config)


@pytest.fixture
def sample_result():
    """テスト用のProcessResultインスタンス"""
    return ProcessResult(
        image_name="test_image.jpg",
        style_analysis=StyleAnalysis(
            category="ナチュラル",
            features=StyleFeatures(
                color="ブラウン",
                cut_technique="レイヤー",
                styling="ストレート",
                impression="フェミニン"
            ),
            keywords=["ナチュラル", "ストレート"]
        ),
        attribute_analysis=AttributeAnalysis(
            sex="レディース",
            length="ミディアム"
        ),
        selected_template=Template(
            category="ナチュラル",
            title="ツヤ感たっぷりのナチュラルミディアム",
            menu="カット+カラー",
            comment="ツヤ感のあるナチュラルスタイルで、大人の女性にピッタリ。",
            hashtag="ナチュラル,ミディアム,ストレート"
        ),
        selected_stylist=StylistInfo(
            name="田中花子",
            specialties="ナチュラルスタイル",
            description="ナチュラルなスタイルが得意なスタイリストです。"
        ),
        selected_coupon=CouponInfo(
            name="ミディアムカット+カラー割引",
            price=10000,
            description="ミディアムヘアのカットとカラーがセットでお得",
            categories=["カット", "カラー"],
            conditions={}
        ),
        processed_at=datetime.now()
    )


def test_get_text_content(text_exporter, sample_result):
    """get_text_content メソッドのテスト"""
    # テキストコンテンツを取得
    text_content = text_exporter.get_text_content([sample_result])
    
    # 期待されるテキストを検証
    assert "【画像名】test_image.jpg" in text_content
    assert "①スタイリスト名: 田中花子" in text_content
    assert "②コメント: ツヤ感のあるナチュラルスタイルで、大人の女性にピッタリ。" in text_content
    assert "③スタイルタイトル: ツヤ感たっぷりのナチュラルミディアム" in text_content
    assert "④性別: レディース" in text_content
    assert "⑤長さ: ミディアム" in text_content
    assert "⑥スタイルメニュー: カット+カラー" in text_content
    assert "⑦クーポン名: ミディアムカット+カラー割引" in text_content
    assert "⑧ハッシュタグ: ナチュラル,ミディアム,ストレート" in text_content


def test_export(text_exporter, sample_result, tmp_path):
    """export メソッドのテスト"""
    # 一時ファイルパスを作成
    output_path = tmp_path / "test_output.txt"
    
    # ファイルにエクスポート
    result_path = text_exporter.export([sample_result], output_path)
    
    # 戻り値が正しいか検証
    assert result_path == output_path
    
    # ファイルが存在するか検証
    assert output_path.exists()
    
    # ファイルの内容を検証
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # テキスト内容の検証
    assert "【画像名】test_image.jpg" in content
    assert "①スタイリスト名: 田中花子" in content
    assert "⑧ハッシュタグ: ナチュラル,ミディアム,ストレート" in content


def test_export_with_existing_file(text_exporter, sample_result, tmp_path):
    """既存ファイルがある場合のexportメソッドのテスト"""
    # 一時ファイルパスを作成
    output_path = tmp_path / "test_output.txt"
    
    # 既存ファイルを作成
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("Existing content")
    
    # バックアップ作成をモック
    with patch.object(text_exporter, '_create_backup') as mock_backup:
        mock_backup.return_value = output_path.with_name(f"{output_path.stem}_backup{output_path.suffix}")
        
        # ファイルにエクスポート
        result_path = text_exporter.export([sample_result], output_path)
    
    # バックアップが呼ばれたか検証
    mock_backup.assert_called_once_with(output_path)
    
    # 戻り値が正しいか検証
    assert result_path == output_path
    
    # ファイルの内容を検証
    with open(output_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 既存の内容が上書きされているか検証
    assert "Existing content" not in content
    assert "【画像名】test_image.jpg" in content


def test_export_error_handling(text_exporter, sample_result, tmp_path):
    """エラーハンドリングのテスト"""
    # 書き込みができないパスを用意
    invalid_path = tmp_path / "nonexistent_dir" / "test_output.txt"
    
    # open関数をモックして例外を発生させる
    with patch('builtins.open') as mock_open:
        mock_open.side_effect = IOError("Test IO Error")
        
        # 例外が発生することを検証
        with pytest.raises(TextExportError) as excinfo:
            text_exporter.export([sample_result], invalid_path)
    
    # エラーメッセージを検証
    assert "テキストファイルの保存に失敗しました" in str(excinfo.value)
    assert "Test IO Error" in str(excinfo.value)


def test_format_result_with_dict(text_exporter):
    """辞書型の結果をフォーマットするテスト"""
    # 辞書型の結果を作成
    dict_result = {
        'image_name': 'dict_test.jpg',
        'selected_stylist': {'name': '山田太郎'},
        'selected_template': {
            'comment': 'テストコメント',
            'title': 'テストタイトル',
            'menu': 'テストメニュー',
            'hashtag': 'テスト,ハッシュタグ'
        },
        'attribute_analysis': {
            'sex': 'メンズ',
            'length': 'ショート'
        },
        'selected_coupon': {'name': 'テストクーポン'}
    }
    
    # フォーマット
    formatted = text_exporter._format_result(dict_result)
    
    # 結果を検証
    assert "【画像名】dict_test.jpg" in formatted
    assert "①スタイリスト名: 山田太郎" in formatted
    assert "②コメント: テストコメント" in formatted
    assert "③スタイルタイトル: テストタイトル" in formatted
    assert "④性別: メンズ" in formatted
    assert "⑤長さ: ショート" in formatted
    assert "⑥スタイルメニュー: テストメニュー" in formatted
    assert "⑦クーポン名: テストクーポン" in formatted
    assert "⑧ハッシュタグ: テスト,ハッシュタグ" in formatted 