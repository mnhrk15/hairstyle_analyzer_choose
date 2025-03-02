"""
ScraperServiceのデモスクリプト

このスクリプトは、ScraperServiceの基本的な使い方を示します。
特定のサロンからスタイリスト情報とクーポン情報を取得し、表示します。
"""

import asyncio
import logging
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.append(str(Path(__file__).parent.parent))

from hairstyle_analyzer.services.scraper import ScraperService
from hairstyle_analyzer.config.models import ScraperConfig
from hairstyle_analyzer.config.loader import ConfigLoader


async def main():
    """
    ScraperServiceのデモを実行します
    """
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 設定の読み込み
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    config_loader = ConfigLoader(config_path)
    scraper_config = config_loader.get_scraper_config()
    
    # キャッシュパスの設定
    cache_path = Path(__file__).parent.parent / "cache" / "scraper_cache.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    # ScraperServiceの初期化
    async with ScraperService(scraper_config, cache_path) as scraper:
        try:
            # サロンのURLを指定（デモ用）
            salon_url = "https://beauty.hotpepper.jp/slnH000570748/"
            
            print(f"サロン {salon_url} からデータを取得中...")
            
            # スタイリスト情報とクーポン情報を並列取得
            stylists, coupons = await scraper.fetch_all_data(salon_url)
            
            # 結果の表示
            print("\n=== スタイリスト情報 ===")
            for i, stylist in enumerate(stylists, 1):
                print(f"[{i}] {stylist.name}")
                if stylist.position:
                    print(f"  役職: {stylist.position}")
                if stylist.description:
                    print(f"  説明: {stylist.description[:50]}..." if len(stylist.description) > 50 else f"  説明: {stylist.description}")
                print()
            
            print("\n=== クーポン情報 ===")
            for i, coupon in enumerate(coupons, 1):
                print(f"[{i}] {coupon.name}")
                if coupon.price:
                    print(f"  価格: {coupon.price}")
                print()
                
            print(f"\n合計: {len(stylists)}人のスタイリスト, {len(coupons)}件のクーポン")
            
        except Exception as e:
            logging.error(f"エラーが発生しました: {str(e)}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
