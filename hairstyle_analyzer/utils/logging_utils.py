"""
ロギングユーティリティモジュール

このモジュールでは、アプリケーション全体で使用するロギング機能を提供します。
ログのフォーマット設定、カスタムフィルター、進捗ロギングなどが含まれます。
"""

import logging
import inspect
import time
import functools
from typing import Callable, TypeVar, Any, Optional, Dict, Union
from pathlib import Path

# 関数の戻り値の型
T = TypeVar('T')


class ContextFilter(logging.Filter):
    """コンテキスト情報を追加するログフィルター"""
    
    def __init__(self, app_name: str = "hairstyle_analyzer"):
        """
        初期化
        
        Args:
            app_name: アプリケーション名
        """
        super().__init__()
        self.app_name = app_name
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        ログレコードにコンテキスト情報を追加する
        
        Args:
            record: ログレコード
            
        Returns:
            常にTrue（フィルタリングは行わない）
        """
        # 呼び出し元の情報を追加
        frame = inspect.currentframe()
        if frame:
            # フレームを遡って呼び出し元を特定
            frame = frame.f_back
            while frame and frame.f_code.co_filename.endswith(('logging_utils.py', 'logging/__init__.py')):
                frame = frame.f_back
            
            if frame:
                record.caller_file = Path(frame.f_code.co_filename).name
                record.caller_function = frame.f_code.co_name
                record.caller_line = frame.f_lineno
        
        # アプリケーション名を追加
        record.app_name = self.app_name
        
        return True


def setup_logger(
    name: str = None,
    level: int = logging.INFO,
    log_file: Optional[Union[str, Path]] = None,
    console: bool = True,
    format_str: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
) -> logging.Logger:
    """
    ロガーをセットアップする
    
    Args:
        name: ロガー名（指定しない場合は呼び出し元のモジュール名）
        level: ログレベル
        log_file: ログファイルのパス（オプション）
        console: コンソール出力を有効にするかどうか
        format_str: ログフォーマット
        
    Returns:
        設定されたロガー
    """
    # ロガー名が指定されていない場合は呼び出し元のモジュール名を使用
    if name is None:
        frame = inspect.currentframe()
        if frame:
            frame = frame.f_back
            if frame:
                module = inspect.getmodule(frame)
                if module:
                    name = module.__name__
    
    # ロガーの取得
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 既存のハンドラをクリア
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # フォーマッターの作成
    formatter = logging.Formatter(format_str)
    
    # コンソールハンドラの追加
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # ファイルハンドラの追加
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # コンテキストフィルターの追加
    logger.addFilter(ContextFilter())
    
    return logger


def log_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> Callable:
    """
    関数の実行時間をログに記録するデコレータ
    
    Args:
        logger: 使用するロガー（指定しない場合は呼び出し元のモジュールのロガー）
        level: ログレベル
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            
            # ロガーが指定されていない場合は関数のモジュールのロガーを使用
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # 関数名を取得
            func_name = func.__name__
            
            # 開始時間を記録
            start_time = time.time()
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # 終了時間を記録
            end_time = time.time()
            execution_time = end_time - start_time
            
            # 実行時間をログに記録
            logger.log(level, f"{func_name} の実行時間: {execution_time:.3f}秒")
            
            return result
        
        return wrapper
    
    return decorator


class ProgressLogger:
    """進捗状況をログに記録するクラス"""
    
    def __init__(
        self,
        total: int,
        logger: Optional[logging.Logger] = None,
        level: int = logging.INFO,
        prefix: str = "進捗",
        interval: int = 10,
        show_time: bool = True
    ):
        """
        初期化
        
        Args:
            total: 処理対象の総数
            logger: 使用するロガー（指定しない場合はルートロガー）
            level: ログレベル
            prefix: ログのプレフィックス
            interval: ログを出力する間隔（パーセント）
            show_time: 経過時間と予測残り時間を表示するかどうか
        """
        self.total = total
        self.logger = logger or logging.getLogger()
        self.level = level
        self.prefix = prefix
        self.interval = interval
        self.show_time = show_time
        
        self.current = 0
        self.start_time = time.time()
        self.last_log_percent = 0
    
    def update(self, increment: int = 1) -> None:
        """
        進捗を更新する
        
        Args:
            increment: 増分
        """
        self.current += increment
        
        # 進捗率を計算
        percent = int(self.current / self.total * 100)
        
        # 前回のログ出力からinterval%以上進んだ場合、または100%に達した場合にログを出力
        if (percent >= self.last_log_percent + self.interval) or (self.current >= self.total):
            # 経過時間を計算
            elapsed_time = time.time() - self.start_time
            
            # メッセージの作成
            message = f"{self.prefix}: {self.current}/{self.total} ({percent}%)"
            
            # 時間情報を追加
            if self.show_time:
                message += f" - 経過時間: {self._format_time(elapsed_time)}"
                
                # 残り時間を予測
                if self.current > 0:
                    # 1アイテムあたりの平均処理時間
                    avg_time_per_item = elapsed_time / self.current
                    # 残りアイテム数
                    remaining_items = self.total - self.current
                    # 残り時間
                    remaining_time = avg_time_per_item * remaining_items
                    
                    message += f", 残り時間: {self._format_time(remaining_time)}"
            
            # ログに出力
            self.logger.log(self.level, message)
            
            # 最後にログを出力した進捗率を更新
            self.last_log_percent = percent
    
    def _format_time(self, seconds: float) -> str:
        """
        時間を読みやすい形式に整形する
        
        Args:
            seconds: 秒数
            
        Returns:
            整形された時間文字列
        """
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}分"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}時間"
