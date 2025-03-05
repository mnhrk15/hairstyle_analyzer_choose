#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
スクレイピングデモプログラム

ホットペッパービューティサイトからスタイリスト情報を取得し、
取得した情報を表示するデモプログラムです。
"""

import asyncio
import logging
import yaml
import os
from pathlib import Path
from typing import List

from hairstyle_analyzer.data.models import ScraperConfig, StylistInfo
from hairstyle_analyzer.services.scraper.scraper_service import ScraperService


async def main():
    """メイン関数"""
    # ロギングの設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    # 設定ファイルの読み込み
    config_path = Path("config/config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config_data = yaml.safe_load(f)
    
    # スクレイパー設定の取得
    scraper_config = ScraperConfig(**config_data["scraper"])
    
    # キャッシュパスの設定
    cache_path = Path("cache/scraper_cache.json")
    os.makedirs(cache_path.parent, exist_ok=True)
    
    # スクレイパーサービスの初期化
    async with ScraperService(scraper_config, cache_path) as scraper:
        # サロンURLの設定（例：アクラ 六甲道）
        salon_url = "https://beauty.hotpepper.jp/slnH000474916/"
        
        # スタイリスト情報の取得
        stylist_data_list = await scraper.get_stylist_links(salon_url)
        logger.info(f"{len(stylist_data_list)}人のスタイリスト情報を取得しました")
        
        # 各スタイリストの情報を作成
        stylists: List[StylistInfo] = []
        for stylist_data in stylist_data_list:
            stylist = await scraper.get_stylist_info(stylist_data)
            stylists.append(stylist)
        
        # 取得した情報を表示
        print("\n===== スタイリスト情報 =====")
        for i, stylist in enumerate(stylists, 1):
            print(f"\n【スタイリスト {i}】")
            print(f"名前: {stylist.name}")
            print(f"得意な技術・特徴: {stylist.specialties}")
            print(f"説明文: {stylist.description}")
            print("-" * 50)


if __name__ == "__main__":
    asyncio.run(main())
