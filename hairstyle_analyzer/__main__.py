"""
ヘアスタイル画像解析システムのメインエントリーポイント

このモジュールは、コマンドラインからアプリケーションを実行するためのエントリーポイントです。
"""

import argparse
import logging
import sys
from pathlib import Path

from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.ui.streamlit_app import run_streamlit_app


def parse_args():
    """コマンドライン引数をパースする"""
    parser = argparse.ArgumentParser(description="ヘアスタイル画像解析システム")
    
    parser.add_argument(
        "--config", "-c",
        type=str,
        help="設定ファイルのパス",
        default="config/config.yaml"
    )
    
    parser.add_argument(
        "--image-folder", "-i",
        type=str,
        help="画像フォルダのパス"
    )
    
    parser.add_argument(
        "--template", "-t",
        type=str,
        help="テンプレートCSVファイルのパス"
    )
    
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="出力Excelファイルのパス"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="デバッグモードを有効にする"
    )
    
    parser.add_argument(
        "--ui", "-u",
        action="store_true",
        help="StreamlitのUIを起動する"
    )
    
    return parser.parse_args()


def main():
    """アプリケーションのメイン関数"""
    # コマンドライン引数のパース
    args = parse_args()
    
    try:
        # 設定マネージャーの作成
        config_manager = ConfigManager(args.config)
        
        # コマンドライン引数による設定の上書き
        config_overrides = {}
        
        if args.image_folder:
            config_overrides["paths"] = config_overrides.get("paths", {})
            config_overrides["paths"]["image_folder"] = args.image_folder
        
        if args.template:
            config_overrides["paths"] = config_overrides.get("paths", {})
            config_overrides["paths"]["template_csv"] = args.template
        
        if args.output:
            config_overrides["paths"] = config_overrides.get("paths", {})
            config_overrides["paths"]["output_excel"] = args.output
        
        if args.debug:
            config_overrides["logging"] = config_overrides.get("logging", {})
            config_overrides["logging"]["log_level"] = "DEBUG"
        
        # 設定の上書きと検証
        if config_overrides:
            config_manager.update_config(config_overrides)
        
        config_manager.validate()
        
        # アプリケーションの実行
        if args.ui:
            # StreamlitのUIを起動
            run_streamlit_app(config_manager)
        else:
            # コマンドラインモードでの実行（未実装）
            logging.error("コマンドラインモードは未実装です。--uiオプションを使用してください。")
            sys.exit(1)
    
    except Exception as e:
        logging.error(f"アプリケーション実行エラー: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
