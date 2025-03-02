"""
ロギング設定モジュール

このモジュールでは、アプリケーション全体で使用するロギングシステムの初期化と設定を行います。
ロガーの階層、ログレベル、ログローテーションなどを設定します。
"""

import os
import sys
import logging
import logging.handlers
from pathlib import Path
from typing import Optional, Dict, Any, Union

from ..data.models import LoggingConfig


def initialize_logging(config: LoggingConfig, app_name: str = "hairstyle_analyzer") -> logging.Logger:
    """
    アプリケーション全体のロギングを初期化する
    
    Args:
        config: ロギング設定
        app_name: アプリケーション名
        
    Returns:
        ルートロガー
    """
    # ルートロガーの取得
    root_logger = logging.getLogger()
    
    # 既存のハンドラをクリア
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # ログレベルの設定
    log_level = getattr(logging, config.log_level.upper(), logging.INFO)
    root_logger.setLevel(log_level)
    
    # ログフォーマッタの作成
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(name)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラの追加
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)
    
    # ファイルハンドラの追加
    if config.log_file:
        log_dir = config.log_file.parent
        log_dir.mkdir(parents=True, exist_ok=True)
        
        # ログローテーションを設定
        file_handler = logging.handlers.RotatingFileHandler(
            config.log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        root_logger.addHandler(file_handler)
    
    # アプリケーション名をログに含める
    class ContextFilter(logging.Filter):
        def filter(self, record):
            record.app_name = app_name
            return True
    
    context_filter = ContextFilter()
    root_logger.addFilter(context_filter)
    
    # 初期メッセージ
    root_logger.info(f"{app_name} ロギングシステムが初期化されました (レベル: {config.log_level})")
    
    return root_logger


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    名前付きロガーを取得する
    
    Args:
        name: ロガー名
        level: ログレベル（オプション）
        
    Returns:
        設定されたロガー
    """
    logger = logging.getLogger(name)
    
    if level is not None:
        logger.setLevel(level)
    
    return logger


def set_log_level(level: Union[str, int], logger_name: Optional[str] = None) -> None:
    """
    ログレベルを変更する
    
    Args:
        level: 新しいログレベル
        logger_name: ロガー名（指定しない場合はルートロガー）
    """
    # レベルが文字列の場合は定数に変換
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # ロガーの取得
    logger = logging.getLogger(logger_name) if logger_name else logging.getLogger()
    
    # レベルの設定
    logger.setLevel(level)
    
    # ハンドラのレベルも更新
    for handler in logger.handlers:
        handler.setLevel(level)
    
    logger.info(f"ログレベルを {logging.getLevelName(level)} に変更しました")


def get_log_info() -> Dict[str, Any]:
    """
    現在のロギング設定情報を取得する
    
    Returns:
        ロギング設定情報を含む辞書
    """
    root_logger = logging.getLogger()
    
    handlers_info = []
    for handler in root_logger.handlers:
        handler_type = type(handler).__name__
        handler_level = logging.getLevelName(handler.level)
        
        if isinstance(handler, logging.FileHandler):
            output = handler.baseFilename
        elif isinstance(handler, logging.StreamHandler):
            output = "stdout" if handler.stream == sys.stdout else "stderr"
        else:
            output = str(handler)
        
        handlers_info.append({
            'type': handler_type,
            'level': handler_level,
            'output': output
        })
    
    return {
        'root_level': logging.getLevelName(root_logger.level),
        'handlers': handlers_info,
        'disabled': root_logger.disabled
    }
