"""
CacheManagerのユニットテスト
"""

import os
import json
import time
import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.data.models import CacheConfig, CacheEntry
from hairstyle_analyzer.utils.errors import AppError


class TestCacheManager(unittest.TestCase):
    """CacheManagerのテストケース"""
    
    def setUp(self):
        """テストの前処理"""
        # 一時ディレクトリの作成
        self.temp_dir = tempfile.TemporaryDirectory()
        self.cache_file_path = Path(self.temp_dir.name) / "test_cache.json"
        
        # キャッシュ設定
        self.config = CacheConfig(
            ttl_days=1,
            max_size=10
        )
        
        # テスト対象のインスタンス作成
        self.cache_manager = CacheManager(self.cache_file_path, self.config)
    
    def tearDown(self):
        """テストの後処理"""
        # 一時ディレクトリの削除
        self.temp_dir.cleanup()
    
    def test_set_and_get(self):
        """データの設定と取得テスト"""
        # データの設定
        test_key = "test_key"
        test_value = {"name": "テストデータ", "value": 123}
        self.cache_manager.set(test_key, test_value)
        
        # データの取得
        retrieved_value = self.cache_manager.get(test_key)
        
        # 取得したデータが正しいことを確認
        self.assertEqual(retrieved_value, test_value)
    
    def test_get_nonexistent_key(self):
        """存在しないキーの取得テスト"""
        # 存在しないキーを取得
        retrieved_value = self.cache_manager.get("nonexistent_key")
        
        # Noneが返されることを確認
        self.assertIsNone(retrieved_value)
    
    def test_set_with_context(self):
        """コンテキスト付きのデータ設定テスト"""
        # 同じキーで異なるコンテキストのデータを設定
        test_key = "test_key"
        test_value1 = {"name": "テストデータ1"}
        test_value2 = {"name": "テストデータ2"}
        
        self.cache_manager.set(test_key, test_value1, context="context1")
        self.cache_manager.set(test_key, test_value2, context="context2")
        
        # 異なるコンテキストで取得
        retrieved_value1 = self.cache_manager.get(test_key, context="context1")
        retrieved_value2 = self.cache_manager.get(test_key, context="context2")
        
        # 正しいデータが取得できることを確認
        self.assertEqual(retrieved_value1, test_value1)
        self.assertEqual(retrieved_value2, test_value2)
    
    def test_set_with_ttl(self):
        """TTL付きのデータ設定テスト"""
        # 短いTTL（0.1秒）でデータを設定
        test_key = "test_key_ttl"
        test_value = {"name": "一時的なデータ"}
        
        self.cache_manager.set(test_key, test_value, ttl=0.1)
        
        # すぐに取得するとデータが存在する
        self.assertEqual(self.cache_manager.get(test_key), test_value)
        
        # TTL経過後にはデータが存在しない
        time.sleep(0.2)
        self.assertIsNone(self.cache_manager.get(test_key))
    
    def test_clear_all(self):
        """全キャッシュクリアテスト"""
        # 複数のデータを設定
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", "value2")
        self.cache_manager.set("key3", "value3")
        
        # すべてのキャッシュをクリア
        cleared_count = self.cache_manager.clear()
        
        # クリアされた数が正しいことを確認
        self.assertEqual(cleared_count, 3)
        
        # すべてのキーが存在しないことを確認
        self.assertIsNone(self.cache_manager.get("key1"))
        self.assertIsNone(self.cache_manager.get("key2"))
        self.assertIsNone(self.cache_manager.get("key3"))
    
    def test_clear_with_pattern(self):
        """パターン指定のキャッシュクリアテスト"""
        # 異なるパターンのキーでデータを設定
        self.cache_manager.set("prefix1_key1", "value1")
        self.cache_manager.set("prefix1_key2", "value2")
        self.cache_manager.set("prefix2_key1", "value3")
        
        # prefix1で始まるキーのみをクリア
        cleared_count = self.cache_manager.clear(pattern="prefix1")
        
        # クリアされた数が正しいことを確認
        self.assertEqual(cleared_count, 2)
        
        # prefix1のキーが存在しないことを確認
        self.assertIsNone(self.cache_manager.get("prefix1_key1"))
        self.assertIsNone(self.cache_manager.get("prefix1_key2"))
        
        # prefix2のキーは残っていることを確認
        self.assertEqual(self.cache_manager.get("prefix2_key1"), "value3")
    
    def test_enforce_size_limit(self):
        """サイズ制限適用テスト"""
        # 設定よりも多くのデータを追加
        for i in range(self.config.max_size + 5):
            # 異なるタイムスタンプを作るために少し待機
            time.sleep(0.01)
            self.cache_manager.set(f"key{i}", f"value{i}")
        
        # キャッシュサイズが制限内に収まっていることを確認
        self.assertLessEqual(len(self.cache_manager.cache), self.config.max_size)
        
        # 最新のデータが残っていることを確認（最後に追加した5つ）
        for i in range(self.config.max_size, self.config.max_size + 5):
            self.assertEqual(self.cache_manager.get(f"key{i}"), f"value{i}")
        
        # 最も古いデータが削除されていることを確認（最初に追加した5つ）
        for i in range(5):
            self.assertIsNone(self.cache_manager.get(f"key{i}"))
    
    def test_cleanup_expired(self):
        """期限切れデータのクリーンアップテスト"""
        # 標準のTTLでデータを設定
        self.cache_manager.set("normal_key", "normal_value")
        
        # 過去のタイムスタンプで期限切れのデータを直接キャッシュに追加
        past_time = time.time() - (self.config.ttl_days * 24 * 60 * 60 + 10)
        expired_entry = CacheEntry(data="expired_value", timestamp=past_time, ttl=None)
        self.cache_manager.cache["expired_key"] = expired_entry
        
        # クリーンアップを実行
        cleaned_count = self.cache_manager._cleanup_expired()
        
        # 1つクリーンアップされたことを確認
        self.assertEqual(cleaned_count, 1)
        
        # 期限切れのキーが存在しないことを確認
        self.assertIsNone(self.cache_manager.get("expired_key"))
        
        # 有効なキーは残っていることを確認
        self.assertEqual(self.cache_manager.get("normal_key"), "normal_value")
    
    def test_save_and_load_cache(self):
        """キャッシュの保存と読み込みテスト"""
        # データの設定
        self.cache_manager.set("key1", "value1")
        self.cache_manager.set("key2", {"nested": "value2"})
        
        # 明示的に保存
        self.cache_manager._save_cache()
        
        # 新しいインスタンスを作成して読み込む
        new_manager = CacheManager(self.cache_file_path, self.config)
        
        # データが正しく読み込まれていることを確認
        self.assertEqual(new_manager.get("key1"), "value1")
        self.assertEqual(new_manager.get("key2"), {"nested": "value2"})
    
    def test_make_cache_key(self):
        """キャッシュキー生成テスト"""
        # 通常のキー
        key = self.cache_manager._make_cache_key("simple_key")
        self.assertEqual(key, "simple_key")
        
        # コンテキスト付きのキー
        key_with_context = self.cache_manager._make_cache_key("key", "context")
        
        # コンテキスト付きのキーはMD5ハッシュ値になっている
        self.assertNotEqual(key_with_context, "key")
        self.assertNotEqual(key_with_context, "key:context")
        self.assertEqual(len(key_with_context), 32)  # MD5ハッシュの長さ
    
    def test_get_statistics(self):
        """統計情報取得テスト"""
        # 標準のデータを設定
        self.cache_manager.set("key1", "value1")
        
        # 過去のタイムスタンプで期限切れのデータを直接キャッシュに追加
        past_time = time.time() - (self.config.ttl_days * 24 * 60 * 60 + 10)
        expired_entry = CacheEntry(data="expired_value", timestamp=past_time, ttl=None)
        self.cache_manager.cache["expired_key"] = expired_entry
        
        # 統計情報を取得
        stats = self.cache_manager.get_statistics()
        
        # 基本的な統計情報があることを確認
        self.assertEqual(stats['total_entries'], 2)
        self.assertEqual(stats['valid_entries'], 1)
        self.assertEqual(stats['expired_entries'], 1)
        self.assertEqual(stats['size_limit'], self.config.max_size)
        self.assertEqual(stats['ttl_days'], self.config.ttl_days)
        self.assertEqual(stats['cache_file'], str(self.cache_file_path))
    
    def test_cleanup(self):
        """キャッシュクリーンアップテスト"""
        # 標準のデータを設定
        for i in range(self.config.max_size + 2):
            self.cache_manager.set(f"key{i}", f"value{i}")
        
        # 過去のタイムスタンプで期限切れのデータを直接キャッシュに追加
        past_time = time.time() - (self.config.ttl_days * 24 * 60 * 60 + 10)
        for i in range(3):
            expired_entry = CacheEntry(data=f"expired_value{i}", timestamp=past_time, ttl=None)
            self.cache_manager.cache[f"expired_key{i}"] = expired_entry
        
        # キャッシュ保存
        self.cache_manager._save_cache()
        
        # クリーンアップを実行
        cleaned_count = self.cache_manager.cleanup()
        
        # クリーンアップされた数が正しいことを確認（期限切れ3）
        self.assertEqual(cleaned_count, 3)
        
        # キャッシュサイズが制限内に収まっていることを確認
        self.assertEqual(len(self.cache_manager.cache), self.config.max_size)


if __name__ == '__main__':
    unittest.main()
