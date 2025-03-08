#!/usr/bin/env python
"""
非同期処理のデモスクリプト

このスクリプトでは、新しく実装された非同期コンテキストマネージャーを使用して
画像処理を効率的に行う例を示します。
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# 相対インポートのためにパスを調整
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.services.gemini.gemini_service import GeminiService
from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.core.processor import MainProcessor
from hairstyle_analyzer.utils.async_context import asynccontextmanager, progress_tracker
from hairstyle_analyzer.core.excel_exporter import ExcelExporter
from hairstyle_analyzer.core.style_matching import StyleMatchingService


async def perform_image_analysis(image_paths: List[Path], config_manager: ConfigManager):
    """
    非同期コンテキストマネージャーを使用して画像分析を実行します
    
    Args:
        image_paths: 分析対象の画像パスリスト
        config_manager: 設定マネージャーインスタンス
    """
    logger = logging.getLogger(__name__)
    logger.info(f"{len(image_paths)}枚の画像を処理します")
    
    # 必要なコンポーネントを初期化
    cache_manager = CacheManager(config_manager.cache)
    template_manager = TemplateManager(config_manager.templates)
    gemini_service = GeminiService(config_manager.gemini)
    
    # 画像アナライザーを初期化
    image_analyzer = ImageAnalyzer(
        gemini_service=gemini_service,
        cache_manager=cache_manager,
        use_cache=True
    )
    
    # テンプレートマッチャーを初期化
    template_matcher = TemplateMatcher(
        gemini_service=gemini_service,
        template_manager=template_manager
    )
    
    # スタイルマッチングサービスを初期化
    style_matcher = StyleMatchingService(gemini_service)
    
    # Excelエクスポーターを初期化
    excel_exporter = ExcelExporter()
    
    # メインプロセッサーを初期化
    processor = MainProcessor(
        image_analyzer=image_analyzer,
        template_matcher=template_matcher,
        style_matcher=style_matcher,
        excel_exporter=excel_exporter,
        cache_manager=cache_manager,
        batch_size=3,
        api_delay=1.0,
        use_cache=True
    )
    
    # 進捗表示用のコールバック関数
    def progress_callback(current, total, message=""):
        percentage = int(current / total * 100) if total > 0 else 0
        logger.info(f"進捗: {percentage}% ({current}/{total}) - {message}")
    
    # 非同期処理を使用して画像を処理
    async with progress_tracker(len(image_paths), progress_callback) as tracker:
        for i, image_path in enumerate(image_paths):
            logger.info(f"画像処理開始: {image_path.name}")
            
            try:
                # 画像処理を実行
                result = await processor.process_single_image(image_path)
                
                if result:
                    logger.info(f"画像処理成功: {image_path.name}")
                    logger.info(f"カテゴリ: {result.style_analysis.category}")
                    logger.info(f"性別: {result.attribute_analysis.sex}")
                    logger.info(f"長さ: {result.attribute_analysis.length}")
                else:
                    logger.error(f"画像処理に失敗しました: {image_path.name}")
                
            except Exception as e:
                logger.error(f"処理エラー: {str(e)}")
            
            # 進捗を更新
            tracker.update(i + 1, f"画像 {image_path.name} 処理完了")
    
    logger.info("すべての画像処理が完了しました")


async def main():
    """メインの実行関数"""
    # 設定マネージャー初期化
    config_manager = ConfigManager()
    config_manager.load()
    
    # 処理対象の画像パスを取得
    image_dir = Path("samples")
    if not image_dir.exists():
        logging.error(f"画像ディレクトリが見つかりません: {image_dir}")
        return
    
    # 画像パスのリストを作成
    image_paths = list(image_dir.glob("*.jpg")) + list(image_dir.glob("*.png"))
    if not image_paths:
        logging.error(f"画像が見つかりません: {image_dir}")
        return
    
    logging.info(f"{len(image_paths)}枚の画像を処理します")
    
    # 画像処理を実行
    await perform_image_analysis(image_paths, config_manager)


if __name__ == "__main__":
    # 非同期メインの実行
    asyncio.run(main()) 