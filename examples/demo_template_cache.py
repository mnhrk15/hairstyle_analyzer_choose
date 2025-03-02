"""
TemplateManagerとCacheManagerのデモンストレーション

このスクリプトは、TemplateManagerとCacheManagerの基本的な使用方法を示します。
"""

import os
import sys
import time
import logging
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.data.models import CacheConfig, StyleAnalysis, StyleFeatures


def setup_logging():
    """ロギング設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )


def demo_template_manager():
    """TemplateManagerのデモ"""
    logger = logging.getLogger("TemplateManagerDemo")
    logger.info("=== TemplateManagerデモ開始 ===")
    
    # テンプレートファイルのパス
    template_path = project_root / "assets" / "templates" / "template.csv"
    
    # TemplateManagerの初期化
    template_manager = TemplateManager(template_path)
    
    # 利用可能なカテゴリを表示
    categories = template_manager.get_all_categories()
    logger.info(f"利用可能なカテゴリ: {', '.join(categories)}")
    
    # テンプレート数を表示
    templates_count = len(template_manager.get_all_templates())
    logger.info(f"テンプレート総数: {templates_count}")
    
    # 特定のカテゴリのテンプレートを表示
    if categories:
        category = categories[0]
        templates = template_manager.get_templates_by_category(category)
        logger.info(f"カテゴリ '{category}' のテンプレート数: {len(templates)}")
        
        if templates:
            template = templates[0]
            logger.info(f"サンプルテンプレート: {template.title}")
            logger.info(f"メニュー: {template.menu}")
            logger.info(f"コメント: {template.comment}")
            logger.info(f"ハッシュタグ: {template.get_hashtags()}")
    
    # 最適なテンプレートの検索例
    features = StyleFeatures(
        color="透明感のあるブラウン",
        cut_technique="レイヤーカット",
        styling="ストレート",
        impression="ナチュラル"
    )
    
    # 実際に存在するカテゴリを使用
    category = categories[0] if categories else "ショート・ボブ"
    
    analysis = StyleAnalysis(
        category=category,
        features=features,
        keywords=["ショートヘア", "小顔", "簡単スタイリング"]
    )
    
    try:
        best_template = template_manager.find_best_template(analysis)
        
        if best_template:
            logger.info("最適なテンプレートを見つけました:")
            logger.info(f"タイトル: {best_template.title}")
            logger.info(f"メニュー: {best_template.menu}")
            logger.info(f"コメント: {best_template.comment}")
        else:
            logger.warning("最適なテンプレートは見つかりませんでした")
    except Exception as e:
        logger.error(f"テンプレート検索中にエラーが発生しました: {e}")
    
    logger.info("=== TemplateManagerデモ終了 ===\n")


def demo_cache_manager():
    """CacheManagerのデモ"""
    logger = logging.getLogger("CacheManagerDemo")
    logger.info("=== CacheManagerデモ開始 ===")
    
    # キャッシュファイルのパス
    cache_dir = project_root / "cache"
    cache_dir.mkdir(exist_ok=True)
    cache_path = cache_dir / "demo_cache.json"
    
    # キャッシュ設定
    config = CacheConfig(ttl_days=1, max_size=100)
    
    # CacheManagerの初期化
    cache_manager = CacheManager(cache_path, config)
    
    # キャッシュにデータを設定
    logger.info("キャッシュにデータを設定しています...")
    cache_manager.set("key1", "Simple value")
    cache_manager.set("key2", {"name": "Nested value", "data": [1, 2, 3]})
    cache_manager.set("temp_key", "Temporary value", ttl=5.0)  # 5秒のTTL
    
    # コンテキスト付きのデータを設定
    cache_manager.set("user_data", {"preferences": "default"}, context="user1")
    cache_manager.set("user_data", {"preferences": "custom"}, context="user2")
    
    # キャッシュからデータを取得
    logger.info("キャッシュからデータを取得しています...")
    value1 = cache_manager.get("key1")
    value2 = cache_manager.get("key2")
    temp_value = cache_manager.get("temp_key")
    
    logger.info(f"key1: {value1}")
    logger.info(f"key2: {value2}")
    logger.info(f"temp_key: {temp_value}")
    
    # コンテキスト付きのデータを取得
    user1_data = cache_manager.get("user_data", context="user1")
    user2_data = cache_manager.get("user_data", context="user2")
    
    logger.info(f"user1のデータ: {user1_data}")
    logger.info(f"user2のデータ: {user2_data}")
    
    # TTLの動作確認
    logger.info("TTLのテスト: 6秒待機...")
    time.sleep(6)
    
    # TTL経過後に再度取得
    temp_value_after = cache_manager.get("temp_key")
    logger.info(f"6秒後のtemp_key: {temp_value_after}")
    
    # キャッシュ統計情報
    stats = cache_manager.get_statistics()
    logger.info("キャッシュ統計情報:")
    for key, value in stats.items():
        logger.info(f"  {key}: {value}")
    
    # 部分的なキャッシュクリア
    cleared_count = cache_manager.clear(pattern="key")
    logger.info(f"'key'を含むキーをクリアしました: {cleared_count}件")
    
    # 検証
    logger.info("キャッシュをクリアした後のデータ:")
    logger.info(f"key1: {cache_manager.get('key1')}")
    logger.info(f"user_data (user1): {cache_manager.get('user_data', context='user1')}")
    
    # 全キャッシュクリア
    cleared_count = cache_manager.clear()
    logger.info(f"全キャッシュをクリアしました: {cleared_count}件")
    
    logger.info("=== CacheManagerデモ終了 ===\n")


def main():
    """メイン関数"""
    setup_logging()
    
    # TemplateManagerのデモ
    demo_template_manager()
    
    # CacheManagerのデモ
    demo_cache_manager()


if __name__ == "__main__":
    main()
