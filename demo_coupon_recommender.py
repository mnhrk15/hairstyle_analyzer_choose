#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
クーポン推薦デモスクリプト

このスクリプトは、指定された画像とサロンURLから、
画像に最適なクーポンを推薦します。
"""

import asyncio
import sys
import yaml
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from hairstyle_analyzer.services.scraper.scraper_service import ScraperService
from hairstyle_analyzer.services.gemini.gemini_service import GeminiService
from hairstyle_analyzer.data.models import ScraperConfig, GeminiConfig


async def main(image_path: str, salon_url: str):
    """メイン関数
    
    Args:
        image_path: 画像ファイルのパス
        salon_url: サロンのURL
    """
    # 画像パスの検証
    image_file = Path(image_path)
    if not image_file.exists():
        print(f"エラー: 画像ファイル '{image_path}' が見つかりません")
        return
    
    # 設定ファイルを読み込む
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    # 設定を作成
    scraper_config = ScraperConfig(**config_data["scraper"])
    
    # Gemini設定を作成し、APIキーを環境変数から取得
    gemini_config_data = config_data["gemini"].copy()
    gemini_config_data["api_key"] = os.getenv("GEMINI_API_KEY")
    
    if not gemini_config_data["api_key"]:
        print("エラー: GEMINI_API_KEYが設定されていません")
        print("プロジェクトルートに.envファイルを作成し、GEMINI_API_KEY=your_api_key_here を設定してください")
        return
    
    gemini_config = GeminiConfig(**gemini_config_data)
    
    # サービスのインスタンスを作成
    scraper = ScraperService(config=scraper_config)
    gemini = GeminiService(config=gemini_config)
    
    try:
        # 1. クーポン情報を取得
        print(f"サロン「{salon_url}」のクーポン情報を取得中...")
        coupons = await scraper.get_coupons(salon_url)
        print(f"取得したクーポン数: {len(coupons)}")
        
        if not coupons:
            print("クーポンが見つかりませんでした")
            return
        
        # 2. 画像分析
        print(f"画像「{image_path}」を分析中...")
        categories = ["ショート", "ボブ", "ミディアム", "ロング", "メンズ", "アレンジ", "パーマ", "カラー"]
        analysis = await gemini.analyze_image(image_file, categories)
        
        if not analysis:
            print("画像分析に失敗しました")
            return
        
        print(f"分析結果: カテゴリ={analysis.category}")
        print(f"特徴:")
        print(f"  髪色: {analysis.features.color}")
        print(f"  カット技法: {analysis.features.cut_technique}")
        print(f"  スタイリング: {analysis.features.styling}")
        print(f"  印象: {analysis.features.impression}")
        
        # 3. 属性分析
        attributes = await gemini.analyze_attributes(image_file)
        if attributes:
            print(f"属性: 性別={attributes.sex}, 長さ={attributes.length}")
        
        # 4. 最適なクーポンを選択
        print("\n最適なクーポンを選択中...")
        recommended_coupon, selection_reason = await gemini.select_coupon(image_file, coupons, analysis)
        
        if not recommended_coupon:
            print("クーポンの選択に失敗しました")
            return
        
        # 5. 結果を表示
        print("\n=== おすすめクーポン ===")
        print(f"名前: {recommended_coupon.name}")
        print(f"価格: {recommended_coupon.price}円")
        print(f"説明: {recommended_coupon.description}")
        print(f"カテゴリ: {recommended_coupon.categories}")
        print(f"条件:")
        for key, value in recommended_coupon.conditions.items():
            print(f"  - {key}: {value}")
        
        # 選択理由を表示
        if selection_reason:
            print(f"\n選択理由: {selection_reason}")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="画像に最適なクーポンを推薦します")
    parser.add_argument("image_path", help="ヘアスタイル画像のパス")
    parser.add_argument("--salon_url", default="https://beauty.hotpepper.jp/slnH000474916/", 
                        help="サロンのURL (デフォルト: https://beauty.hotpepper.jp/slnH000474916/)")
    
    args = parser.parse_args()
    
    # 非同期メイン関数を実行
    asyncio.run(main(args.image_path, args.salon_url))
