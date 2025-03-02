"""
エラーとエラーハンドリングモジュール

このモジュールは、アプリケーション全体で使用される例外クラスとエラーハンドリング機能を定義します。
"""

import sys
import logging
import traceback
import functools
from typing import Dict, Any, Optional, Type, Callable, TypeVar, Union, List
from pathlib import Path

# 関数の戻り値の型
T = TypeVar('T')


# ベース例外クラス
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
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message} - 詳細: {self.details}"
        return self.message


# 設定関連の例外
class ConfigError(AppError):
    """設定関連のエラー"""
    
    def __init__(self, message: str, config_file: Optional[str] = None, config_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            config_file: 設定ファイルパス（オプション）
            config_key: 設定キー（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if config_file:
            details['config_file'] = config_file
        if config_key:
            details['config_key'] = config_key
        super().__init__(message, details)
        self.config_file = config_file
        self.config_key = config_key


# API関連の例外
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


class GeminiAPIError(APIError):
    """Gemini API特有のエラー"""
    
    def __init__(self, message: str, status_code: Optional[int] = None, error_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            status_code: ステータスコード（オプション）
            error_type: Gemini APIのエラータイプ（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if error_type:
            details['error_type'] = error_type
        super().__init__(message, "Gemini API", status_code, details)
        self.error_type = error_type


# スクレイピング関連の例外
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


# HTML解析エラー
class HTMLParseError(ScraperError):
    """HTML解析エラー"""
    
    def __init__(self, message: str, url: str, selector: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            url: スクレイピング対象のURL
            selector: CSS/XPathセレクタ（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if selector:
            details['selector'] = selector
        super().__init__(message, url, details)
        self.selector = selector


# HTTP関連エラー
class HTTPError(ScraperError):
    """HTTPリクエスト関連のエラー"""
    
    def __init__(self, message: str, url: str, status_code: Optional[int] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            url: リクエスト先のURL
            status_code: HTTPステータスコード（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if status_code:
            details['status_code'] = status_code
        super().__init__(message, url, details)
        self.status_code = status_code


# 画像処理関連の例外
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


class ImageError(ProcessingError):
    """画像ファイル関連のエラー"""
    
    def __init__(self, message: str, image_path: str, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            image_path: 画像パス
            details: 追加の詳細情報（オプション）
        """
        super().__init__(message, image_path, details)


class AnalysisError(ProcessingError):
    """画像分析関連のエラー"""
    
    def __init__(self, message: str, image_path: Optional[str] = None, analysis_type: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            image_path: 画像パス（オプション）
            analysis_type: 分析タイプ（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if analysis_type:
            details['analysis_type'] = analysis_type
        super().__init__(message, image_path, details)
        self.analysis_type = analysis_type


# 入力検証関連の例外
class ValidationError(AppError):
    """入力検証関連のエラー"""
    
    def __init__(self, message: str, field: Optional[str] = None, value: Optional[Any] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            field: フィールド名（オプション）
            value: 無効な値（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = str(value)
        super().__init__(message, details)
        self.field = field
        self.value = value


# リソース関連の例外
class ResourceError(AppError):
    """リソース関連のエラー"""
    
    def __init__(self, message: str, resource_type: Optional[str] = None, resource_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            resource_type: リソースタイプ（オプション）
            resource_path: リソースパス（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if resource_type:
            details['resource_type'] = resource_type
        if resource_path:
            details['resource_path'] = resource_path
        super().__init__(message, details)
        self.resource_type = resource_type
        self.resource_path = resource_path


class FileNotFoundError(ResourceError):
    """ファイルが見つからないエラー"""
    
    def __init__(self, message: str, file_path: str, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            file_path: ファイルパス
            details: 追加の詳細情報（オプション）
        """
        super().__init__(message, "file", file_path, details)
        self.file_path = file_path


class PermissionError(ResourceError):
    """権限エラー"""
    
    def __init__(self, message: str, resource_path: str, operation: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            resource_path: リソースパス
            operation: 操作タイプ（例: 'read', 'write'）（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if operation:
            details['operation'] = operation
        super().__init__(message, "permission", resource_path, details)
        self.resource_path = resource_path
        self.operation = operation


# テンプレート関連の例外
class TemplateError(AppError):
    """テンプレート関連のエラー"""
    
    def __init__(self, message: str, template_file: Optional[str] = None, template_key: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            template_file: テンプレートファイルパス（オプション）
            template_key: テンプレートキー（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if template_file:
            details['template_file'] = template_file
        if template_key:
            details['template_key'] = template_key
        super().__init__(message, details)
        self.template_file = template_file
        self.template_key = template_key


# Excel出力関連の例外
class ExcelExportError(AppError):
    """Excel出力関連のエラー"""
    
    def __init__(self, message: str, output_path: Optional[str] = None, sheet_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            output_path: 出力パス（オプション）
            sheet_name: シート名（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if output_path:
            details['output_path'] = output_path
        if sheet_name:
            details['sheet_name'] = sheet_name
        super().__init__(message, details)
        self.output_path = output_path
        self.sheet_name = sheet_name


# エラーハンドリング関数
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


def format_error_message(error: Exception) -> str:
    """
    例外からユーザーフレンドリーなエラーメッセージを生成する
    
    Args:
        error: 例外オブジェクト
        
    Returns:
        ユーザーフレンドリーなエラーメッセージ
    """
    if isinstance(error, AppError):
        # アプリケーション独自の例外の場合
        return f"{error.message}"
    else:
        # その他の例外の場合
        return f"エラーが発生しました: {str(error)}"


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


def async_with_error_handling(
    error_type: Type[AppError] = AppError,
    error_message: str = "非同期処理中にエラーが発生しました",
    logger: Optional[logging.Logger] = None,
    raise_original: bool = False,
    return_on_error: Optional[Any] = None,
    log_level: int = logging.ERROR
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    非同期関数用のエラーハンドリングデコレータ
    
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
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal logger
            logger = logger or logging.getLogger(func.__module__)
            
            try:
                return await func(*args, **kwargs)
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
    def global_exception_handler(exctype, value, tb):
        """グローバルな例外ハンドラ"""
        logger = logging.getLogger("global")
        logger.error("捕捉されていない例外:", exc_info=(exctype, value, tb))
        
        # 元の例外ハンドラを呼び出す（通常はsys.__excepthook__）
        sys.__excepthook__(exctype, value, traceback.print_tb(tb))
    
    # グローバルな例外ハンドラを設定
    sys.excepthook = global_exception_handler


# エラーメッセージをより具体的にするヘルパー関数
def get_detailed_error_message(error: Exception) -> str:
    """
    例外から詳細なエラーメッセージを生成する
    
    Args:
        error: 例外オブジェクト
        
    Returns:
        詳細なエラーメッセージ
    """
    if isinstance(error, GeminiAPIError):
        return f"Gemini APIエラー: {error.message}" + (f" (ステータスコード: {error.status_code})" if error.status_code else "")
    
    elif isinstance(error, APIError):
        return f"API「{error.api_name}」エラー: {error.message}" + (f" (ステータスコード: {error.status_code})" if error.status_code else "")
    
    elif isinstance(error, HTTPError):
        return f"HTTPエラー: {error.message} - URL: {error.url}" + (f" (ステータスコード: {error.status_code})" if error.status_code else "")
    
    elif isinstance(error, HTMLParseError):
        return f"HTML解析エラー: {error.message} - URL: {error.url}" + (f" (セレクタ: {error.selector})" if error.selector else "")
    
    elif isinstance(error, ScraperError):
        return f"スクレイピングエラー: {error.message} - URL: {error.url}"
    
    elif isinstance(error, ImageError):
        return f"画像エラー: {error.message} - ファイル: {Path(error.image_path).name}"
    
    elif isinstance(error, AnalysisError):
        msg = f"分析エラー: {error.message}"
        if error.image_path:
            msg += f" - ファイル: {Path(error.image_path).name}"
        if error.analysis_type:
            msg += f" (分析タイプ: {error.analysis_type})"
        return msg
    
    elif isinstance(error, ProcessingError):
        msg = f"処理エラー: {error.message}"
        if error.image_path:
            msg += f" - ファイル: {Path(error.image_path).name}"
        return msg
    
    elif isinstance(error, ValidationError):
        msg = f"検証エラー: {error.message}"
        if error.field:
            msg += f" - フィールド: {error.field}"
        return msg
    
    elif isinstance(error, FileNotFoundError):
        return f"ファイルが見つかりません: {error.message} - パス: {error.file_path}"
    
    elif isinstance(error, PermissionError):
        msg = f"権限エラー: {error.message} - パス: {error.resource_path}"
        if error.operation:
            msg += f" (操作: {error.operation})"
        return msg
    
    elif isinstance(error, ResourceError):
        msg = f"リソースエラー: {error.message}"
        if error.resource_type:
            msg += f" - タイプ: {error.resource_type}"
        if error.resource_path:
            msg += f" - パス: {error.resource_path}"
        return msg
    
    elif isinstance(error, TemplateError):
        msg = f"テンプレートエラー: {error.message}"
        if error.template_file:
            msg += f" - ファイル: {error.template_file}"
        if error.template_key:
            msg += f" (キー: {error.template_key})"
        return msg
    
    elif isinstance(error, ExcelExportError):
        msg = f"Excel出力エラー: {error.message}"
        if error.output_path:
            msg += f" - ファイル: {error.output_path}"
        if error.sheet_name:
            msg += f" (シート: {error.sheet_name})"
        return msg
    
    elif isinstance(error, ConfigError):
        msg = f"設定エラー: {error.message}"
        if error.config_file:
            msg += f" - ファイル: {error.config_file}"
        if error.config_key:
            msg += f" (キー: {error.config_key})"
        return msg
    
    elif isinstance(error, AppError):
        return f"アプリケーションエラー: {error.message}"
    
    else:
        return f"エラー: {str(error)}"


# エラーを分類するヘルパー関数
def classify_error(error: Exception) -> Dict[str, Any]:
    """
    エラーを分類し、構造化された情報を返す
    
    Args:
        error: 例外オブジェクト
        
    Returns:
        エラーの分類情報
    """
    result = {
        'type': type(error).__name__,
        'message': str(error),
        'is_app_error': isinstance(error, AppError),
        'category': 'unknown',
        'severity': 'error',
        'details': {}
    }
    
    # エラーカテゴリの分類
    if isinstance(error, (GeminiAPIError, APIError)):
        result['category'] = 'api'
    elif isinstance(error, (ScraperError, HTTPError, HTMLParseError)):
        result['category'] = 'scraping'
    elif isinstance(error, (ImageError, AnalysisError, ProcessingError)):
        result['category'] = 'processing'
    elif isinstance(error, (ValidationError)):
        result['category'] = 'validation'
    elif isinstance(error, (FileNotFoundError, PermissionError, ResourceError)):
        result['category'] = 'resource'
    elif isinstance(error, (TemplateError)):
        result['category'] = 'template'
    elif isinstance(error, (ExcelExportError)):
        result['category'] = 'export'
    elif isinstance(error, (ConfigError)):
        result['category'] = 'config'
    
    # アプリケーション独自の例外の場合は詳細情報を追加
    if isinstance(error, AppError):
        result['details'] = error.details
    
    # 重要度の判定
    if isinstance(error, (APIError, ProcessingError, TemplateError, ExcelExportError)):
        result['severity'] = 'error'
    elif isinstance(error, (ValidationError, ResourceError, ConfigError)):
        result['severity'] = 'warning'
    elif isinstance(error, (ScraperError)):
        # スクレイピングエラーはHTTPステータスコードによって重要度を判定
        if isinstance(error, HTTPError) and error.status_code:
            if 400 <= error.status_code < 500:
                result['severity'] = 'warning'
            elif 500 <= error.status_code < 600:
                result['severity'] = 'error'
        else:
            result['severity'] = 'warning'
    
    return result


# 複数のエラーを集約するためのユーティリティ
class ErrorCollector:
    """複数のエラーを収集するクラス"""
    
    def __init__(self):
        """初期化"""
        self.errors: List[Exception] = []
    
    def add(self, error: Exception) -> None:
        """
        エラーを追加
        
        Args:
            error: 追加する例外
        """
        self.errors.append(error)
    
    def has_errors(self) -> bool:
        """
        エラーがあるかどうかを確認
        
        Returns:
            エラーがある場合はTrue、そうでない場合はFalse
        """
        return len(self.errors) > 0
    
    def raise_if_errors(self, combine: bool = True) -> None:
        """
        エラーがある場合は例外を発生させる
        
        Args:
            combine: 複数のエラーを1つにまとめるかどうか
        
        Raises:
            AppError: エラーがある場合
        """
        if not self.has_errors():
            return
        
        if combine and len(self.errors) > 1:
            # 複数のエラーを1つにまとめる
            error_messages = [get_detailed_error_message(error) for error in self.errors]
            raise AppError(
                f"{len(self.errors)}件のエラーが発生しました",
                {'errors': error_messages}
            )
        else:
            # 最初のエラーを再スロー
            raise self.errors[0]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        エラー概要を取得
        
        Returns:
            エラー概要情報
        """
        if not self.has_errors():
            return {'has_errors': False, 'count': 0}
        
        # エラーの分類と集計
        categories = {}
        severities = {}
        
        for error in self.errors:
            classification = classify_error(error)
            category = classification['category']
            severity = classification['severity']
            
            categories[category] = categories.get(category, 0) + 1
            severities[severity] = severities.get(severity, 0) + 1
        
        return {
            'has_errors': True,
            'count': len(self.errors),
            'categories': categories,
            'severities': severities,
            'first_error': get_detailed_error_message(self.errors[0]) if self.errors else None
        }
