#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
クーポン情報スクレイピングのデモスクリプト

このスクリプトは、指定されたサロンURLからクーポン情報を取得し、
取得した情報を表示します。
"""

import asyncio
import sys
import yaml
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from hairstyle_analyzer.services.scraper.scraper_service import ScraperService
from hairstyle_analyzer.data.models import ScraperConfig


async def main():
    """メイン関数"""
    # サロンURL（実在するサロンのURLに変更）
    salon_url = "https://beauty.hotpepper.jp/slnH000474916/"
    
    # 設定ファイルを読み込む
    config_path = project_root / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    # ScraperConfigを作成
    scraper_config = ScraperConfig(**config_data["scraper"])
    
    # ScraperServiceのインスタンスを作成
    scraper = ScraperService(config=scraper_config)
    
    try:
        # クーポン情報を取得
        print(f"サロン「{salon_url}」のクーポン情報を取得中...")
        coupons = await scraper.get_coupons(salon_url)
        
        # 結果を表示
        print(f"\n取得したクーポン数: {len(coupons)}")
        
        # すべてのクーポン情報を表示
        print("\n=== すべてのクーポン情報 ===")
        for i, coupon in enumerate(coupons, 1):
            print(f"\nクーポン {i}:")
            print(f"名前: {coupon.name}")
            print(f"価格: {coupon.price}円")
            print(f"説明: {coupon.description}")
            print(f"カテゴリ: {coupon.categories}")
            print(f"条件:")
            for key, value in coupon.conditions.items():
                print(f"  - {key}: {value}")
            print("-" * 50)
        
        # 統計情報
        if coupons:
            avg_price = sum(coupon.price for coupon in coupons) / len(coupons)
            min_price = min(coupon.price for coupon in coupons)
            max_price = max(coupon.price for coupon in coupons)
            
            print("\n=== クーポン統計情報 ===")
            print(f"平均価格: {avg_price:.0f}円")
            print(f"最低価格: {min_price}円")
            print(f"最高価格: {max_price}円")
            
            # カテゴリ別のクーポン数
            category_counts = {}
            for coupon in coupons:
                for category in coupon.categories:
                    category_counts[category] = category_counts.get(category, 0) + 1
            
            print("\n=== カテゴリ別クーポン数 ===")
            for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
                print(f"{category}: {count}件")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")


if __name__ == "__main__":
    asyncio.run(main())
