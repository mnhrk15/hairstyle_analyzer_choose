"""
キャッシュデコレータモジュール

このモジュールでは、キャッシュ機能を提供するデコレータを定義しています。
関数やメソッドのキャッシュを簡単に実装するためのユーティリティを提供します。
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar, cast, Dict

# 型変数の定義
T = TypeVar('T')
CacheKeyFunction = Callable[..., str]


def cacheable(cache_key_fn: CacheKeyFunction):
    """
    関数の結果をキャッシュするデコレータ。
    
    このデコレータは、指定された関数の結果をキャッシュします。
    キャッシュの使用可否は、use_cacheパラメータまたはインスタンスの設定によって制御できます。
    
    Args:
        cache_key_fn: キャッシュキーを生成する関数
        
    Returns:
        デコレータ関数
        
    使用例:
    ```python
    @cacheable(lambda self, image_path, *args, **kwargs: f"analysis:{image_path.name}")
    async def analyze_image(self, image_path, ...):
        # 実際の処理
    ```
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def async_wrapper(self, *args, **kwargs) -> T:
            # キャッシュマネージャーの存在確認
            if not hasattr(self, 'cache_manager') or self.cache_manager is None:
                return await func(self, *args, **kwargs)
                
            # キャッシュ使用の判定
            use_cache = kwargs.pop('use_cache', None)
            should_use_cache = getattr(self, 'use_cache', False) if use_cache is None else use_cache
            
            # キャッシュを使用しない場合は直接関数を実行
            if not should_use_cache:
                return await func(self, *args, **kwargs)
            
            # キャッシュキーの生成
            cache_key = cache_key_fn(self, *args, **kwargs)
            logger = logging.getLogger(__name__)
            
            # キャッシュから結果を取得
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"キャッシュヒット: {cache_key}")
                return cast(T, cached_result)
            
            # キャッシュにない場合は関数を実行
            result = await func(self, *args, **kwargs)
            
            # 結果をキャッシュに保存（Noneでない場合のみ）
            if result is not None:
                self.cache_manager.set(cache_key, result)
                logger.debug(f"キャッシュに保存: {cache_key}")
            
            return result
        
        @functools.wraps(func)
        def sync_wrapper(self, *args, **kwargs) -> T:
            # キャッシュマネージャーの存在確認
            if not hasattr(self, 'cache_manager') or self.cache_manager is None:
                return func(self, *args, **kwargs)
                
            # キャッシュ使用の判定
            use_cache = kwargs.pop('use_cache', None)
            should_use_cache = getattr(self, 'use_cache', False) if use_cache is None else use_cache
            
            # キャッシュを使用しない場合は直接関数を実行
            if not should_use_cache:
                return func(self, *args, **kwargs)
            
            # キャッシュキーの生成
            cache_key = cache_key_fn(self, *args, **kwargs)
            logger = logging.getLogger(__name__)
            
            # キャッシュから結果を取得
            cached_result = self.cache_manager.get(cache_key)
            if cached_result is not None:
                logger.debug(f"キャッシュヒット: {cache_key}")
                return cast(T, cached_result)
            
            # キャッシュにない場合は関数を実行
            result = func(self, *args, **kwargs)
            
            # 結果をキャッシュに保存（Noneでない場合のみ）
            if result is not None:
                self.cache_manager.set(cache_key, result)
                logger.debug(f"キャッシュに保存: {cache_key}")
            
            return result
        
        # 非同期関数かどうかで適切なラッパーを返す
        if asyncio_iscoroutinefunction_safe(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def asyncio_iscoroutinefunction_safe(func: Callable) -> bool:
    """
    関数が非同期関数かどうかを安全に判定します。
    
    Args:
        func: 判定する関数
        
    Returns:
        非同期関数の場合はTrue、それ以外はFalse
    """
    try:
        import asyncio
        return asyncio.iscoroutinefunction(func)
    except (ImportError, AttributeError):
        # asyncioモジュールがない場合や、iscoroutinefunction関数がない場合
        return False


def memoize(func: Callable[..., T]) -> Callable[..., T]:
    """
    関数の結果をインメモリでメモ化するシンプルなデコレータ。
    
    このデコレータは、関数の引数に基づいて結果をメモ化します。
    キャッシュマネージャーを必要としない、軽量なメモ化実装です。
    
    Args:
        func: メモ化する関数
        
    Returns:
        メモ化された関数
    """
    cache: Dict[str, Any] = {}
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> T:
        # キャッシュキーの生成（引数の文字列表現を使用）
        key = str(args) + str(sorted(kwargs.items()))
        
        # キャッシュに結果があれば返す
        if key in cache:
            return cast(T, cache[key])
        
        # 結果を計算してキャッシュに保存
        result = func(*args, **kwargs)
        cache[key] = result
        return result
    
    return wrapper 