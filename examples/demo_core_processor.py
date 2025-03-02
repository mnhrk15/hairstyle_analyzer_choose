"""
コアプロセッサーのデモンストレーション

このスクリプトは、MainProcessorの基本的な使用方法を示します。
画像処理、テンプレートマッチング、スタイリスト・クーポン選択、Excel出力の一連のフローをテストします。
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.services.gemini import GeminiService
from hairstyle_analyzer.services.scraper import ScraperService
from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.core.style_matching import StyleMatchingService
from hairstyle_analyzer.core.excel_exporter import ExcelExporter
from hairstyle_analyzer.core.processor import MainProcessor


def setup_logging():
    """ロギング設定"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # 特定のモジュールのログレベルを調整
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def progress_callback(current, total, message=""):
    """進捗コールバック関数"""
    # Simple progress display
    if message:
        print(f"Progress: [{current}/{total}] - {message}")
    else:
        percent = int(current / total * 100) if total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * current / total) if total > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f"\rProgress: [{current}/{total}] [{bar}] {percent}%", end="")
        if current == total:
            print()  # New line when complete


async def demo_main_processor():
    """MainProcessorのデモ"""
    logger = logging.getLogger("MainProcessorDemo")
    logger.info("=== MainProcessorデモ開始 ===")
    
    # 環境変数の読み込み
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    
    if not api_key:
        logger.error("Gemini APIキーが設定されていません。")
        logger.error("プロジェクトルートに.envファイルを作成し、GEMINI_API_KEY=your_api_key_here を設定してください。")
        logger.error(".env.exampleを参考にしてください。")
        return
    
    try:
        # 設定ファイルからConfigManagerを初期化
        config_path = project_root / "config" / "config.yaml"
        config_manager = ConfigManager(config_path)
        
        # テンプレートマネージャー初期化
        template_path = config_manager.paths.template_csv
        template_manager = TemplateManager(template_path)
        
        # キャッシュマネージャー初期化
        cache_path = config_manager.paths.cache_file
        cache_manager = CacheManager(cache_path, config_manager.cache)
        
        # GeminiServiceの初期化
        gemini_config = config_manager.gemini
        gemini_config.api_key = api_key
        gemini_service = GeminiService(gemini_config)
        logger.info("GeminiServiceを初期化しました")
        
        # 各コアコンポーネントの初期化
        image_analyzer = ImageAnalyzer(gemini_service, cache_manager)
        template_matcher = TemplateMatcher(template_manager)
        style_matcher = StyleMatchingService(gemini_service)
        excel_exporter = ExcelExporter(config_manager.excel)
        
        # メインプロセッサーの初期化
        processor = MainProcessor(
            image_analyzer=image_analyzer,
            template_matcher=template_matcher,
            style_matcher=style_matcher,
            excel_exporter=excel_exporter,
            cache_manager=cache_manager,
            batch_size=config_manager.processing.batch_size,
            api_delay=config_manager.processing.api_delay
        )
        
        # 進捗コールバックを設定
        processor.set_progress_callback(progress_callback)
        
        # サンプル画像のパス
        sample_image_dir = project_root / "assets" / "samples"
        
        # サンプルディレクトリが存在するか確認
        if not sample_image_dir.exists() or not sample_image_dir.is_dir():
            logger.error(f"サンプル画像ディレクトリが見つかりません: {sample_image_dir}")
            return
        
        # 画像ファイルを取得
        image_files = [f for f in sample_image_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        
        if not image_files:
            logger.error(f"サンプル画像ディレクトリに画像ファイルが見つかりません: {sample_image_dir}")
            return
        
        # テスト用にファイル数を制限
        image_files = image_files[:2]
        logger.info(f"処理対象画像: {[f.name for f in image_files]}")
        
        # スクレイパーの初期化とスタイリスト・クーポン情報の取得
        try:
            # スクレイパー初期化
            scraper_config = config_manager.scraper
            cache_file = project_root / "cache" / "scraper_cache.json"
            async with ScraperService(scraper_config, cache_file) as scraper:
                logger.info(f"サロンデータの取得中... URL: {scraper_config.base_url}")
                stylists, coupons = await scraper.fetch_all_data(scraper_config.base_url)
                logger.info(f"サロンデータ取得完了: {len(stylists)}人のスタイリスト, {len(coupons)}件のクーポン")
            
            # 外部データを使用した画像処理
            logger.info("外部データを使用した画像処理を開始...")
            results = await processor.process_images_with_external_data(image_files, stylists, coupons)
            logger.info(f"画像処理完了: {len(results)}/{len(image_files)}枚")
            
        except Exception as e:
            logger.error(f"スクレイピングエラーまたは画像処理エラー: {str(e)}")
            logger.info("スクレイピングなしで画像処理を継続します...")
            
            # 単純な画像処理を実行（スタイリスト・クーポン情報なし）
            results = await processor.process_images(image_files)
            logger.info(f"画像処理完了: {len(results)}/{len(image_files)}枚")
        
        # 結果の表示
        if results:
            logger.info("\n処理結果の概要:")
            for i, result in enumerate(results, 1):
                logger.info(f"画像 {i}: {result.image_name}")
                logger.info(f"  カテゴリ: {result.style_analysis.category}")
                logger.info(f"  性別: {result.attribute_analysis.sex}")
                logger.info(f"  髪の長さ: {result.attribute_analysis.length}")
                logger.info(f"  スタイルタイトル: {result.selected_template.title}")
                logger.info(f"  スタイリスト: {result.selected_stylist.name}")
                logger.info(f"  クーポン: {result.selected_coupon.name}")
                logger.info("---")
            
            # Excel出力
            output_dir = project_root / "output"
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "demo_results.xlsx"
            
            try:
                excel_path = processor.export_to_excel(output_path)
                logger.info(f"Excel出力完了: {excel_path}")
            except Exception as e:
                logger.error(f"Excel出力エラー: {e}")
        else:
            logger.warning("処理結果がありません")
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    logger.info("=== MainProcessorデモ終了 ===")


def main():
    """メイン関数"""
    setup_logging()
    
    # 非同期関数を実行
    asyncio.run(demo_main_processor())


if __name__ == "__main__":
    main()
