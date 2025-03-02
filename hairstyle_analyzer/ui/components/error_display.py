"""
エラー表示コンポーネントモジュール

このモジュールでは、Streamlit UIでのエラー表示に関するコンポーネントを定義します。
ユーザーフレンドリーなエラーメッセージと詳細情報の表示、エラー種類に応じた表示スタイルなどを提供します。
"""

import traceback
import logging
from typing import Optional, Dict, Any, List, Union, Type
import streamlit as st

from ...utils.errors import (
    AppError, APIError, GeminiAPIError, ScraperError, ProcessingError,
    ValidationError, ResourceError, TemplateError, ExcelExportError,
    get_detailed_error_message, classify_error
)


# エラータイプに応じたアイコンマッピング
ERROR_ICONS = {
    'api': '🌐',
    'scraping': '🔍',
    'processing': '🖼️',
    'validation': '⚠️',
    'resource': '📁',
    'template': '📝',
    'export': '📊',
    'config': '⚙️',
    'unknown': '❓'
}

# エラー重要度に応じた色マッピング
SEVERITY_COLORS = {
    'error': 'red',
    'warning': 'orange',
    'info': 'blue',
    'success': 'green'
}


def display_error(
    error: Union[Exception, str],
    title: Optional[str] = None,
    show_details: bool = False,
    container: Optional[Any] = None
) -> None:
    """
    エラーを表示する
    
    Args:
        error: 表示する例外またはエラーメッセージ
        title: エラータイトル（指定しない場合は自動生成）
        show_details: 詳細情報を表示するかどうか
        container: 表示するコンテナ（指定しない場合はst.error）
    """
    container = container or st
    
    # エラーメッセージの準備
    if isinstance(error, Exception):
        # 例外オブジェクトの場合
        error_obj = error
        error_message = get_detailed_error_message(error)
        
        # エラー分類の取得
        classification = classify_error(error)
        error_category = classification['category']
        error_severity = classification['severity']
        error_details = classification['details']
        
        # アイコンと色の取得
        icon = ERROR_ICONS.get(error_category, ERROR_ICONS['unknown'])
        color = SEVERITY_COLORS.get(error_severity, 'red')
        
        # タイトルの自動生成（指定されていない場合）
        if title is None:
            title = f"{icon} {error_category.capitalize()} Error"
    else:
        # 文字列の場合
        error_obj = None
        error_message = str(error)
        icon = ERROR_ICONS['unknown']
        color = SEVERITY_COLORS['error']
        error_details = {}
        
        # タイトルの自動生成（指定されていない場合）
        if title is None:
            title = f"{icon} Error"
    
    # エラーメッセージの表示
    if error_severity == 'error':
        container.error(f"**{title}**")
        container.error(error_message)
    elif error_severity == 'warning':
        container.warning(f"**{title}**")
        container.warning(error_message)
    else:
        container.error(f"**{title}**")
        container.error(error_message)
    
    # 詳細情報の表示（オプション）
    if show_details and error_obj is not None:
        with container.expander("詳細情報"):
            # エラータイプの表示
            st.write(f"**エラータイプ:** {type(error_obj).__name__}")
            
            # 詳細情報の表示（AppErrorの場合）
            if isinstance(error_obj, AppError) and error_details:
                st.write("**詳細情報:**")
                for key, value in error_details.items():
                    st.write(f"- {key}: {value}")
            
            # スタックトレースの表示
            if hasattr(error_obj, '__traceback__') and error_obj.__traceback__:
                st.write("**スタックトレース:**")
                trace_lines = traceback.format_exception(
                    type(error_obj), error_obj, error_obj.__traceback__
                )
                st.code(''.join(trace_lines))


def display_multiple_errors(
    errors: List[Exception],
    title: str = "複数のエラーが発生しました",
    container: Optional[Any] = None
) -> None:
    """
    複数のエラーをまとめて表示する
    
    Args:
        errors: 表示する例外のリスト
        title: エラータイトル
        container: 表示するコンテナ（指定しない場合はst.error）
    """
    container = container or st
    
    if not errors:
        return
    
    # エラー数の表示
    container.error(f"**{title}** ({len(errors)}件)")
    
    # エラーごとに表示
    for i, error in enumerate(errors, 1):
        error_message = get_detailed_error_message(error)
        container.error(f"{i}. {error_message}")
    
    # 詳細表示のエクスパンダー
    with container.expander("詳細情報"):
        for i, error in enumerate(errors, 1):
            st.write(f"**エラー {i}**")
            st.write(f"タイプ: {type(error).__name__}")
            
            if isinstance(error, AppError) and hasattr(error, 'details'):
                st.write("詳細:")
                for key, value in error.details.items():
                    st.write(f"- {key}: {value}")
            
            st.write("---")


class StreamlitErrorHandler:
    """Streamlit用のエラーハンドラークラス"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初期化
        
        Args:
            logger: 使用するロガー（指定しない場合はルートロガー）
        """
        self.logger = logger or logging.getLogger()
        self.errors = []
    
    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        self.errors = []
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        コンテキストマネージャーの終了処理
        
        Args:
            exc_type: 例外の型
            exc_val: 例外の値
            exc_tb: トレースバック
            
        Returns:
            例外を処理した場合はTrue、そうでない場合はFalse
        """
        if exc_val:
            # 例外をログに記録
            self.logger.error(f"エラーが発生しました: {exc_val}", exc_info=(exc_type, exc_val, exc_tb))
            
            # エラーを追加
            self.errors.append(exc_val)
            
            # エラーを表示
            display_error(exc_val, show_details=True)
            
            # 例外を処理したことを示す
            return True
        
        return False
    
    def handle(self, func, *args, **kwargs):
        """
        関数を実行し、エラーを処理する
        
        Args:
            func: 実行する関数
            *args: 関数の位置引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            関数の戻り値、またはエラー時はNone
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # 例外をログに記録
            self.logger.error(f"関数 {func.__name__} でエラーが発生しました: {e}", exc_info=True)
            
            # エラーを追加
            self.errors.append(e)
            
            # エラーを表示
            display_error(e, show_details=True)
            
            # エラー時はNoneを返す
            return None
    
    async def handle_async(self, func, *args, **kwargs):
        """
        非同期関数を実行し、エラーを処理する
        
        Args:
            func: 実行する非同期関数
            *args: 関数の位置引数
            **kwargs: 関数のキーワード引数
            
        Returns:
            関数の戻り値、またはエラー時はNone
        """
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            # 例外をログに記録
            self.logger.error(f"非同期関数 {func.__name__} でエラーが発生しました: {e}", exc_info=True)
            
            # エラーを追加
            self.errors.append(e)
            
            # エラーを表示
            display_error(e, show_details=True)
            
            # エラー時はNoneを返す
            return None
    
    def has_errors(self):
        """
        エラーがあるかどうかを確認
        
        Returns:
            エラーがある場合はTrue、そうでない場合はFalse
        """
        return len(self.errors) > 0
    
    def get_errors(self):
        """
        エラーのリストを取得
        
        Returns:
            エラーのリスト
        """
        return self.errors.copy()


def display_validation_errors(errors: Dict[str, str], container: Optional[Any] = None) -> None:
    """
    バリデーションエラーを表示する
    
    Args:
        errors: フィールド名をキー、エラーメッセージを値とする辞書
        container: 表示するコンテナ（指定しない場合はst.error）
    """
    container = container or st
    
    if not errors:
        return
    
    container.error("**入力データにエラーがあります**")
    
    # エラーの表示
    for field, message in errors.items():
        container.error(f"- **{field}**: {message}")


def format_api_error(error: APIError) -> str:
    """
    APIエラーを整形する
    
    Args:
        error: APIエラー
        
    Returns:
        整形されたエラーメッセージ
    """
    if isinstance(error, GeminiAPIError):
        msg = f"Gemini API: {error.message}"
        if error.status_code:
            msg += f" (コード: {error.status_code})"
        if error.error_type:
            msg += f" - タイプ: {error.error_type}"
        return msg
    else:
        msg = f"{error.api_name}: {error.message}"
        if error.status_code:
            msg += f" (コード: {error.status_code})"
        return msg
