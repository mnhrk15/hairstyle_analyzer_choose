"""
非同期コンテキストマネージャーユーティリティモジュール

このモジュールでは、非同期コンテキストマネージャーを簡単に実装するためのユーティリティを提供します。
Python 3.7以上では標準ライブラリの contextlib.asynccontextmanager を使用しますが、
それより前のバージョンでは async_generator パッケージを使用します。
"""

import sys
import asyncio
import inspect
import logging
import functools
from typing import Any, AsyncGenerator, Callable, TypeVar, cast, Optional

# Python 3.7以上では標準ライブラリの asynccontextmanager を使用
if sys.version_info >= (3, 7):
    from contextlib import asynccontextmanager
else:
    try:
        # Python 3.6では async_generator パッケージを使用
        from async_generator import asynccontextmanager
    except ImportError:
        raise ImportError(
            "Python 3.7未満では async_generator パッケージが必要です。"
            "pip install async_generator でインストールしてください。"
        )

# 型変数の定義
T = TypeVar('T')


class AsyncResource:
    """
    非同期リソースを管理するベースクラス
    
    このクラスを継承して、非同期リソースの初期化と解放を実装します。
    """
    
    async def __aenter__(self):
        """非同期コンテキストマネージャーのエントリーポイント"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャーの終了ポイント"""
        await self.cleanup()
        return False  # 例外を伝播する
    
    async def initialize(self):
        """オーバーライドして初期化ロジックを実装"""
        pass
    
    async def cleanup(self):
        """オーバーライドしてクリーンアップロジックを実装"""
        pass


def async_safe(func):
    """
    関数を非同期安全にするデコレータ
    
    同期関数を非同期関数としてラップするか、
    すでに非同期関数の場合はそのまま返します。
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        if inspect.iscoroutinefunction(func):
            return await func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper


class Timer(AsyncResource):
    """
    非同期タイマーの例
    
    指定された秒数の間、非同期的に待機します。
    
    使用例:
    ```python
    async with Timer(duration=2.0) as timer:
        # タイマーが開始される
        print("処理開始")
        
    # 2秒後に終了
    print("処理終了")
    ```
    """
    
    def __init__(self, duration: float, callback: Optional[Callable[[], None]] = None):
        self.duration = duration
        self.callback = callback
        self.start_time = 0.0
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self):
        self.start_time = asyncio.get_event_loop().time()
        self.logger.debug(f"タイマー開始: {self.duration}秒")
    
    async def cleanup(self):
        elapsed = asyncio.get_event_loop().time() - self.start_time
        remaining = max(0, self.duration - elapsed)
        
        if remaining > 0:
            self.logger.debug(f"残り時間: {remaining:.2f}秒")
            await asyncio.sleep(remaining)
        
        if self.callback:
            self.callback()
        
        self.logger.debug("タイマー終了")


@asynccontextmanager
async def progress_tracker(total: int, callback: Callable[[int, int, str], None]):
    """
    非同期進捗トラッカー
    
    総数と進捗コールバック関数を受け取り、進捗を追跡する非同期コンテキストマネージャーを提供します。
    
    使用例:
    ```python
    async with progress_tracker(len(images), update_progress) as tracker:
        for i, image in enumerate(images):
            # 処理実行
            result = await process_image(image)
            # 進捗更新
            tracker.update(i + 1, f"画像 {image.name} を処理中")
    ```
    
    Args:
        total: 処理する項目の総数
        callback: 進捗報告用のコールバック関数 (current, total, message)
    """
    class Tracker:
        def __init__(self):
            self.current = 0
            self.total = total
            self.message = ""
        
        def update(self, current: int, message: str = ""):
            self.current = current
            self.message = message
            callback(current, total, message)
    
    # トラッカーインスタンスを作成して進捗を0に初期化
    tracker = Tracker()
    callback(0, total, "開始")
    
    try:
        # トラッカーをyieldして、with文ブロック内でトラッカーが使用可能に
        yield tracker
    finally:
        # 最終進捗を設定
        if tracker.current < total:
            callback(total, total, "完了（エラーあり）")
        else:
            callback(total, total, "完了") 