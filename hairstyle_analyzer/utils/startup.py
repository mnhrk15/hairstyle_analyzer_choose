"""
アプリケーションスタートアップモジュール

このモジュールでは、アプリケーションの起動時に実行される初期化処理を提供します。
ロギングの設定、エラーハンドリングの初期化、環境のチェックなどを行います。
"""

import sys
import os
import logging
import platform
from typing import Optional, Dict, Any

from .errors import setup_global_exception_handler
from .logging_setup import initialize_logging
from ..data.config_manager import ConfigManager


def initialize_app(
    config_path: Optional[str] = None,
    app_name: str = "hairstyle_analyzer",
    check_environment: bool = True
) -> ConfigManager:
    """
    アプリケーションを初期化する
    
    Args:
        config_path: 設定ファイルのパス（指定しない場合はデフォルト）
        app_name: アプリケーション名
        check_environment: 環境をチェックするかどうか
        
    Returns:
        ConfigManagerインスタンス
    """
    # 設定の読み込み
    config_manager = ConfigManager(config_path)
    
    # ロギングの初期化
    root_logger = initialize_logging(config_manager.logging, app_name)
    
    # グローバル例外ハンドラのセットアップ
    setup_global_exception_handler()
    
    # 環境のチェック（オプション）
    if check_environment:
        env_status = check_environment_compatibility()
        if not env_status['compatible']:
            root_logger.warning(
                f"環境に互換性の問題があります: {', '.join(env_status['issues'])}"
            )
    
    # システム情報のログ出力
    log_system_info(root_logger)
    
    # 設定の検証
    config_manager.validate()
    
    root_logger.info(f"{app_name} の初期化が完了しました")
    
    return config_manager


def check_environment_compatibility() -> Dict[str, Any]:
    """
    実行環境の互換性をチェックする
    
    Returns:
        互換性情報の辞書
    """
    issues = []
    
    # Pythonバージョンのチェック
    python_version = sys.version_info
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 9):
        issues.append(f"Python 3.9以上が必要です。現在のバージョン: {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    # 必要なモジュールのチェック
    required_modules = ['PIL', 'streamlit', 'pandas', 'google.generativeai', 'openpyxl', 'yaml', 'requests', 'bs4']
    missing_modules = []
    
    for module_name in required_modules:
        try:
            __import__(module_name.split('.')[0])
        except ImportError:
            missing_modules.append(module_name)
    
    if missing_modules:
        issues.append(f"以下のモジュールがインストールされていません: {', '.join(missing_modules)}")
    
    # 環境変数のチェック
    if not os.environ.get('GEMINI_API_KEY'):
        issues.append("GEMINI_API_KEY環境変数が設定されていません")
    
    return {
        'compatible': len(issues) == 0,
        'issues': issues,
        'python_version': f"{python_version.major}.{python_version.minor}.{python_version.micro}",
        'missing_modules': missing_modules
    }


def log_system_info(logger: logging.Logger) -> None:
    """
    システム情報をログに出力する
    
    Args:
        logger: ロガー
    """
    logger.info("===== システム情報 =====")
    logger.info(f"Python バージョン: {platform.python_version()}")
    logger.info(f"OS: {platform.system()} {platform.release()} {platform.version()}")
    logger.info(f"マシン: {platform.machine()}")
    logger.info(f"プロセッサ: {platform.processor()}")
    
    try:
        import psutil
        memory = psutil.virtual_memory()
        logger.info(f"メモリ: 合計={memory.total / (1024**3):.1f}GB, 利用可能={memory.available / (1024**3):.1f}GB ({memory.percent}%使用中)")
        logger.info(f"CPUコア数: 物理={psutil.cpu_count(logical=False)}, 論理={psutil.cpu_count(logical=True)}")
    except ImportError:
        logger.info("psutilがインストールされていないため、詳細なシステム情報は利用できません")
    
    try:
        import PIL
        logger.info(f"Pillow バージョン: {PIL.__version__}")
    except (ImportError, AttributeError):
        pass
    
    try:
        import streamlit
        logger.info(f"Streamlit バージョン: {streamlit.__version__}")
    except (ImportError, AttributeError):
        pass
    
    try:
        import pandas
        logger.info(f"pandas バージョン: {pandas.__version__}")
    except (ImportError, AttributeError):
        pass
    
    try:
        import google.generativeai
        logger.info(f"google-generativeai が利用可能")
    except ImportError:
        pass
    
    logger.info("========================")
