"""
エラーハンドリングユーティリティモジュール

このモジュールでは、アプリケーション全体で使用するエラーハンドリング機能を提供します。
カスタム例外クラスの定義、例外デコレータ、ロギングユーティリティなどが含まれます。
"""

import functools
import logging
import sys
import traceback
from typing import Callable, TypeVar, Any, Optional, Type, Dict, Union

# 関数の戻り値の型
T = TypeVar('T')


class AppError(Exception):
    """アプリケーション基本エラークラス"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            details: 追加の詳細情報（オプション）
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigError(AppError):
    """設定関連のエラー"""
    pass


class APIError(AppError):
    """API呼び出し関連のエラー"""
    
    def __init__(self, message: str, api_name: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            api_name: APIの名前
            status_code: ステータスコード（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        details.update({
            'api_name': api_name,
            'status_code': status_code
        })
        super().__init__(message, details)
        self.api_name = api_name
        self.status_code = status_code


class ScraperError(AppError):
    """スクレイピング関連のエラー"""
    
    def __init__(self, message: str, url: str, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            url: スクレイピング対象のURL
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        details['url'] = url
        super().__init__(message, details)
        self.url = url


class ProcessingError(AppError):
    """画像処理関連のエラー"""
    
    def __init__(self, message: str, image_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            image_path: 画像パス（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if image_path:
            details['image_path'] = image_path
        super().__init__(message, details)
        self.image_path = image_path


class ValidationError(AppError):
    """入力検証関連のエラー"""
    pass


class ResourceError(AppError):
    """リソース関連のエラー"""
    pass


def log_error(error: Exception, logger: Optional[logging.Logger] = None) -> None:
    """
    例外をログに記録する
    
    Args:
        error: ログに記録する例外
        logger: 使用するロガー（指定しない場合はルートロガー）
    """
    logger = logger or logging.getLogger()
    
    if isinstance(error, AppError):
        # アプリケーション独自の例外の場合は詳細情報も記録
        error_details = getattr(error, 'details', {})
        error_type = type(error).__name__
        logger.error(f"{error_type}: {error.message} - 詳細: {error_details}")
    else:
        # その他の例外の場合はスタックトレースも記録
        logger.error(f"予期せぬエラー: {str(error)}", exc_info=True)


def with_error_handling(
    error_type: Type[AppError] = AppError,
    error_message: str = "処理中にエラーが発生しました",
    logger: Optional[logging.Logger] = None,
    raise_original: bool = False,
    return_on_error: Optional[Any] = None,
    log_level: int = logging.ERROR
) -> Callable[[Callable[..., T]], Callable[..., Union[T, Any]]]:
    """
    エラーハンドリングを行うデコレータ
    
    Args:
        error_type: 発生した例外を包むエラー型
        error_message: エラーメッセージ
        logger: 使用するロガー（指定しない場合はルートロガー）
        raise_original: 元の例外を再スローするかどうか
        return_on_error: エラー時の戻り値
        log_level: ログレベル
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., Union[T, Any]]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Union[T, Any]:
            nonlocal logger
            logger = logger or logging.getLogger(func.__module__)
            
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # エラーログの記録
                if log_level >= logging.ERROR:
                    logger.error(f"{error_message}: {str(e)}", exc_info=True)
                elif log_level >= logging.WARNING:
                    logger.warning(f"{error_message}: {str(e)}")
                elif log_level >= logging.INFO:
                    logger.info(f"{error_message}: {str(e)}")
                
                # 元の例外を再スローするか、カスタム例外を発生させるか
                if raise_original:
                    raise
                
                # エラーの詳細情報を収集
                details = {
                    'function': func.__name__,
                    'module': func.__module__,
                    'traceback': traceback.format_exc()
                }
                
                # カスタム例外を発生させるが、戻り値が指定されている場合は代わりにそれを返す
                if return_on_error is not None:
                    return return_on_error
                
                raise error_type(error_message, details) from e
                
        return wrapper
    
    return decorator


def setup_global_exception_handler() -> None:
    """グローバルな例外ハンドラをセットアップする"""
    def global_exception_handler(exctype, value, traceback):
        """グローバルな例外ハンドラ"""
        logger = logging.getLogger("global")
        logger.error("捕捉されていない例外:", exc_info=(exctype, value, traceback))
        
        # 元の例外ハンドラを呼び出す（通常はsys.__excepthook__）
        sys.__excepthook__(exctype, value, traceback)
    
    # グローバルな例外ハンドラを設定
    sys.excepthook = global_exception_handler
