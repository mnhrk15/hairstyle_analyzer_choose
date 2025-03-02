"""
キャッシュ管理モジュール

このモジュールでは、アプリケーション全体で使用するキャッシュ管理機能を提供します。
処理結果のキャッシュ、TTLベースの有効期限管理、サイズ制限機能などが含まれます。
"""

import os
import json
import time
import logging
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Set, Union, TypeVar, Generic, Callable
from datetime import datetime, timedelta

from pydantic import ValidationError

from .models import CacheEntry, CacheConfig
from .interfaces import CacheManagerProtocol
from ..utils.errors import AppError, with_error_handling


T = TypeVar('T')


class CacheManager(CacheManagerProtocol):
    """キャッシュ管理クラス
    
    処理結果をファイルにキャッシュし、読み込む機能を提供します。
    TTL（有効期限）ベースの管理、最大サイズ制限、クリーンアップ機能などがあります。
    """
    
    def __init__(self, cache_file_path: Union[str, Path], config: CacheConfig):
        """
        初期化
        
        Args:
            cache_file_path: キャッシュファイルのパス
            config: キャッシュ設定
        """
        self.logger = logging.getLogger(__name__)
        self.cache_file_path = Path(cache_file_path)
        self.config = config
        
        # キャッシュデータのロード
        self.cache: Dict[str, CacheEntry] = {}
        self._load_cache()
    
    @with_error_handling(AppError, "キャッシュファイルの読み込みに失敗しました")
    def _load_cache(self) -> None:
        """
        キャッシュファイルを読み込みます。
        ファイルが存在しない場合や読み込みエラーの場合は、空のキャッシュを使用します。
        """
        if not self.cache_file_path.exists():
            self.logger.info(f"キャッシュファイルが見つかりません: {self.cache_file_path}")
            self.cache = {}
            return
        
        try:
            with open(self.cache_file_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # キャッシュエントリを構築
            self.cache = {}
            for key, entry_data in cache_data.items():
                try:
                    # JSONからCacheEntryを構築
                    self.cache[key] = CacheEntry(
                        data=entry_data.get('data'),
                        timestamp=entry_data.get('timestamp', time.time()),
                        ttl=entry_data.get('ttl')
                    )
                except ValidationError as e:
                    self.logger.warning(f"無効なキャッシュエントリをスキップします: {key} - エラー: {e}")
            
            self.logger.info(f"キャッシュを読み込みました: {len(self.cache)}件のエントリ")
            
            # 古いキャッシュエントリをクリーンアップ
            self._cleanup_expired()
            
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"キャッシュファイルの読み込みエラー: {e}")
            self.cache = {}
    
    @with_error_handling(AppError, "キャッシュファイルの保存に失敗しました")
    def _save_cache(self) -> None:
        """
        現在のキャッシュ状態をファイルに保存します。
        """
        # キャッシュディレクトリが存在することを確認
        cache_dir = self.cache_file_path.parent
        if not cache_dir.exists():
            cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # キャッシュデータを辞書形式に変換
            cache_data = {}
            for key, entry in self.cache.items():
                cache_data[key] = {
                    'data': entry.data,
                    'timestamp': entry.timestamp,
                    'ttl': entry.ttl
                }
            
            # 一時ファイルに書き込み
            temp_file = self.cache_file_path.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
            
            # 一時ファイルを正規のファイルに置き換え
            if temp_file.exists():
                if self.cache_file_path.exists():
                    self.cache_file_path.unlink()
                temp_file.rename(self.cache_file_path)
                
            self.logger.debug(f"キャッシュを保存しました: {len(self.cache)}件のエントリ")
            
        except (IOError, OSError) as e:
            self.logger.error(f"キャッシュファイルの保存エラー: {e}")
            # 一時ファイルが存在する場合はクリーンアップ
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            raise
    
    def _cleanup_expired(self) -> int:
        """
        期限切れのキャッシュエントリを削除します。
        
        Returns:
            削除されたエントリの数
        """
        now = time.time()
        expired_keys = []
        
        # デフォルトのTTL（秒単位）
        default_ttl = self.config.ttl_days * 24 * 60 * 60
        
        # 期限切れのキーを収集
        for key, entry in self.cache.items():
            ttl = entry.ttl or default_ttl
            if now - entry.timestamp > ttl:
                expired_keys.append(key)
        
        # 期限切れのエントリを削除
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            self.logger.info(f"{len(expired_keys)}件の期限切れキャッシュエントリを削除しました")
        
        return len(expired_keys)
    
    def _enforce_size_limit(self) -> int:
        """
        キャッシュサイズを制限値以下に保ちます。
        最も古いエントリから順に削除します。
        
        Returns:
            削除されたエントリの数
        """
        if len(self.cache) <= self.config.max_size:
            return 0
        
        # 削除する必要があるエントリ数
        excess = len(self.cache) - self.config.max_size
        
        # タイムスタンプでソートしたキーのリスト（古い順）
        sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
        
        # 最も古いエントリから削除
        keys_to_remove = sorted_keys[:excess]
        for key in keys_to_remove:
            del self.cache[key]
        
        self.logger.info(f"サイズ制限により{len(keys_to_remove)}件のキャッシュエントリを削除しました")
        
        return len(keys_to_remove)
    
    def get(self, key: str, context: str = "") -> Optional[Any]:
        """
        指定されたキーのキャッシュデータを取得します。
        
        Args:
            key: キャッシュキー
            context: キャッシュコンテキスト（オプション）
            
        Returns:
            キャッシュデータ、または存在しない場合はNone
        """
        # コンテキストがある場合はキーに組み込む
        cache_key = self._make_cache_key(key, context)
        
        # キャッシュにキーが存在しない場合
        if cache_key not in self.cache:
            return None
        
        # キャッシュエントリを取得
        entry = self.cache[cache_key]
        
        # 期限切れかどうかをチェック
        now = time.time()
        default_ttl = self.config.ttl_days * 24 * 60 * 60
        ttl = entry.ttl or default_ttl
        
        if now - entry.timestamp > ttl:
            # 期限切れの場合はエントリを削除
            del self.cache[cache_key]
            self._save_cache()
            return None
        
        self.logger.debug(f"キャッシュヒット: {cache_key}")
        return entry.data
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None, context: str = "") -> None:
        """
        キャッシュにデータを設定します。
        
        Args:
            key: キャッシュキー
            value: キャッシュするデータ
            ttl: 有効期限（秒）（オプション）
            context: キャッシュコンテキスト（オプション）
        """
        # コンテキストがある場合はキーに組み込む
        cache_key = self._make_cache_key(key, context)
        
        # キャッシュエントリを作成
        entry = CacheEntry(
            data=value,
            timestamp=time.time(),
            ttl=ttl
        )
        
        # キャッシュに追加
        self.cache[cache_key] = entry
        
        # サイズ制限をチェック
        self._enforce_size_limit()
        
        # キャッシュを保存
        self._save_cache()
        
        self.logger.debug(f"キャッシュに追加: {cache_key}")
    
    def _make_cache_key(self, key: str, context: str = "") -> str:
        """
        キャッシュキーを生成します。
        
        Args:
            key: ベースキー
            context: コンテキスト情報（オプション）
            
        Returns:
            キャッシュキー
        """
        if not context:
            return key
        
        # キーとコンテキストを組み合わせてハッシュ化
        combined = f"{key}:{context}"
        return hashlib.md5(combined.encode('utf-8')).hexdigest()
    
    def clear(self, pattern: Optional[str] = None) -> int:
        """
        キャッシュをクリアします。
        
        Args:
            pattern: クリアするキーのパターン（オプション）
            
        Returns:
            クリアされたエントリ数
        """
        if pattern is None:
            # 全てのキャッシュをクリア
            count = len(self.cache)
            self.cache = {}
            self._save_cache()
            self.logger.info(f"キャッシュを全てクリアしました: {count}件のエントリ")
            return count
        
        # パターンにマッチするキーを探す
        matched_keys = [k for k in self.cache.keys() if pattern in k]
        
        # マッチしたキーを削除
        for key in matched_keys:
            del self.cache[key]
        
        # キャッシュを保存
        if matched_keys:
            self._save_cache()
            self.logger.info(f"パターン '{pattern}' に一致する{len(matched_keys)}件のエントリを削除しました")
        
        return len(matched_keys)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        キャッシュの統計情報を取得します。
        
        Returns:
            統計情報を含む辞書
        """
        # 現在の時刻
        now = time.time()
        
        # デフォルトTTL
        default_ttl = self.config.ttl_days * 24 * 60 * 60
        
        # 有効なエントリと期限切れのエントリを数える
        total_entries = len(self.cache)
        expired_entries = 0
        
        for entry in self.cache.values():
            ttl = entry.ttl or default_ttl
            if now - entry.timestamp > ttl:
                expired_entries += 1
        
        # 最も古いエントリと最も新しいエントリのタイムスタンプ
        timestamps = [entry.timestamp for entry in self.cache.values()]
        oldest = min(timestamps) if timestamps else 0
        newest = max(timestamps) if timestamps else 0
        
        return {
            'total_entries': total_entries,
            'valid_entries': total_entries - expired_entries,
            'expired_entries': expired_entries,
            'size_limit': self.config.max_size,
            'ttl_days': self.config.ttl_days,
            'oldest_entry_timestamp': oldest,
            'newest_entry_timestamp': newest,
            'cache_file': str(self.cache_file_path)
        }
    
    def cleanup(self) -> int:
        """
        期限切れのエントリを削除し、サイズ制限を適用します。
        
        Returns:
            削除されたエントリの総数
        """
        # 期限切れのエントリを削除
        expired_count = self._cleanup_expired()
        
        # サイズ制限を適用
        size_limit_count = self._enforce_size_limit()
        
        # キャッシュを保存
        if expired_count > 0 or size_limit_count > 0:
            self._save_cache()
        
        return expired_count + size_limit_count
