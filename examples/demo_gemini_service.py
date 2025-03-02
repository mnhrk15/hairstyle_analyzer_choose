"""
GeminiServiceのデモンストレーション

このスクリプトは、GeminiServiceの基本的な使用方法を示します。
APIキーが必要なため、.envファイルか環境変数にGEMINI_API_KEYを設定して実行してください。
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

from hairstyle_analyzer.services.gemini.gemini_service import GeminiService
from hairstyle_analyzer.data.models import GeminiConfig
from hairstyle_analyzer.data.config_manager import ConfigManager


def setup_logging():
    """ロギング設定"""
    logging.basicConfig(
        level=logging.DEBUG,  # DEBUGレベルに設定
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    # 特定のモジュールのログレベルを調整
    logging.getLogger("google").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


async def demo_gemini_service():
    """GeminiServiceのデモ"""
    logger = logging.getLogger("GeminiServiceDemo")
    logger.info("=== GeminiServiceデモ開始 ===")
    
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
        
        # GeminiConfigを取得して、APIキーを設定
        gemini_config = config_manager.gemini
        gemini_config.api_key = api_key
        
        # GeminiServiceの初期化
        service = GeminiService(gemini_config)
        logger.info("GeminiServiceを初期化しました")
        
        # サンプル画像のパス
        sample_image_dir = project_root / "assets" / "samples"
        
        # サンプルディレクトリが存在するか確認
        if not sample_image_dir.exists() or not sample_image_dir.is_dir():
            logger.error(f"サンプル画像ディレクトリが見つかりません: {sample_image_dir}")
            return
        
        # 最初の画像ファイルを取得
        image_files = [f for f in sample_image_dir.iterdir() 
                      if f.is_file() and f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
        
        if not image_files:
            logger.error(f"サンプル画像ディレクトリに画像ファイルが見つかりません: {sample_image_dir}")
            return
        
        sample_image = image_files[0]
        logger.info(f"サンプル画像: {sample_image.name}")
        
        # カテゴリ一覧の取得
        categories = config_manager.get_all_categories()
        logger.info(f"利用可能なカテゴリ: {', '.join(categories)}")
        
        # 画像分析
        logger.info("画像分析を実行しています...")
        try:
            # categories は形式に合うように渡す
            analysis = await service.analyze_image(sample_image, categories)
            
            if analysis:
                logger.info("分析結果:")
                logger.info(f"カテゴリ: {analysis.category}")
                logger.info(f"特徴:")
                logger.info(f"  - 髪色: {analysis.features.color}")
                logger.info(f"  - カット技法: {analysis.features.cut_technique}")
                logger.info(f"  - スタイリング: {analysis.features.styling}")
                logger.info(f"  - 印象: {analysis.features.impression}")
                logger.info(f"キーワード: {', '.join(analysis.keywords)}")
            else:
                logger.warning("分析結果が得られませんでした")
            
            # 属性分析
            logger.info("\n属性分析を実行しています...")
            # この呼び出しには特別なパラメータは不要
            attributes = await service.analyze_attributes(sample_image)
            
            if attributes:
                logger.info("属性分析結果:")
                logger.info(f"性別: {attributes.sex}")
                logger.info(f"髪の長さ: {attributes.length}")
            else:
                logger.warning("属性分析結果が得られませんでした")
            
            # === スタイリスト選択とクーポン選択のサンプルコード（実行時にはコメント解除） ===
            """
            # スタイリスト選択のサンプル
            logger.info("\nスタイリスト選択のサンプルを実行...")
            
            # サンプルスタイリストデータ
            sample_stylists = [
                {
                    "name": "鈴木健太",
                    "description": "カットとカラーが得意なスタイリスト。ロングスタイルの仕上がりには定評があります。",
                    "position": "トップスタイリスト"
                },
                {
                    "name": "佐藤美咲",
                    "description": "ショートヘアとボブスタイルが得意。トレンドを取り入れたスタイル提案が好評。",
                    "position": "チーフスタイリスト"
                },
                {
                    "name": "田中優子",
                    "description": "パーマとヘアアレンジのスペシャリスト。フェミニンなスタイルが得意です。",
                    "position": "スタイリスト"
                }
            ]
            
            # Pydantic モデルに変換
            from hairstyle_analyzer.data.models import StylistInfo
            stylists = [StylistInfo(**stylist) for stylist in sample_stylists]
            
            # スタイリスト選択の実行
            selected_stylist = await service.select_stylist(sample_image, stylists, analysis)
            
            if selected_stylist:
                logger.info("選択されたスタイリスト:")
                logger.info(f"名前: {selected_stylist.name}")
                logger.info(f"役職: {selected_stylist.position}")
                logger.info(f"説明: {selected_stylist.description}")
            else:
                logger.warning("スタイリストを選択できませんでした")
            
            # クーポン選択のサンプル
            logger.info("\nクーポン選択のサンプルを実行...")
            
            # サンプルクーポンデータ
            sample_coupons = [
                {
                    "name": "カット+カラー",
                    "description": "髪を切ってカラーリングするセットメニュー",
                    "price": 12000
                },
                {
                    "name": "カット+パーマ",
                    "description": "髪を切ってパーマをかけるセットメニュー",
                    "price": 15000
                },
                {
                    "name": "トリートメント",
                    "description": "髪に栄養を与え、ツヤとまとまりを出すメニュー",
                    "price": 8000
                }
            ]
            
            # Pydantic モデルに変換
            from hairstyle_analyzer.data.models import CouponInfo
            coupons = [CouponInfo(**coupon) for coupon in sample_coupons]
            
            # クーポン選択の実行
            selected_coupon = await service.select_coupon(sample_image, coupons, analysis)
            
            if selected_coupon:
                logger.info("選択されたクーポン:")
                logger.info(f"名前: {selected_coupon.name}")
                logger.info(f"説明: {selected_coupon.description}")
                logger.info(f"価格: {selected_coupon.price}円")
            else:
                logger.warning("クーポンを選択できませんでした")
            """
            # === サンプルコード終了 ===
        
        except Exception as e:
            logger.error(f"分析中にエラーが発生しました: {str(e)}")
    
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}")
    
    logger.info("=== GeminiServiceデモ終了 ===")


def main():
    """メイン関数"""
    setup_logging()
    
    # 非同期関数を実行
    asyncio.run(demo_gemini_service())


if __name__ == "__main__":
    main()
