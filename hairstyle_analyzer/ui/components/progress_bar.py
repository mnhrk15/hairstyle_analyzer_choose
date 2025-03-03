"""
プログレスバーコンポーネントモジュール

このモジュールでは、Streamlitで使用するプログレスバーコンポーネントを提供します。
処理進捗の視覚化、経過時間と残り時間の表示などの機能が含まれます。
"""

import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

import streamlit as st


class ProgressBar:
    """
    Streamlit用プログレスバークラス
    
    処理の進捗状況を視覚的に表示し、経過時間と残り時間の計算を行います。
    """
    
    def __init__(self, total: int, title: str = "処理進捗", auto_refresh: bool = True):
        """
        初期化
        
        Args:
            total: 処理の総数
            title: プログレスバーのタイトル
            auto_refresh: 自動更新を行うかどうか
        """
        self.total = max(1, total)  # 0除算防止
        self.title = title
        self.auto_refresh = auto_refresh
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.message = ""
        self.complete = False
        
        # Streamlitウィジェット用のキー
        self.bar_key = f"progress_bar_{id(self)}"
        self.status_key = f"progress_status_{id(self)}"
        self.time_key = f"progress_time_{id(self)}"
        
        # ウィジェットの初期化
        self._init_widgets()
    
    def _init_widgets(self) -> None:
        """ウィジェットを初期化する"""
        if self.title:
            st.write(f"### {self.title}")
        
        # プログレスバーの作成
        self.progress_bar = st.progress(0, key=self.bar_key)
        
        # ステータステキストの表示
        self.status_text = st.empty()
        self.status_text.text("準備中...")
        
        # 時間情報の表示
        self.time_text = st.empty()
    
    def update(self, current: int, message: str = "") -> None:
        """
        進捗状況を更新する
        
        Args:
            current: 現在の処理数
            message: 表示するメッセージ
        """
        self.current = min(current, self.total)
        self.message = message
        now = time.time()
        
        # 更新間隔の制限（頻繁すぎる更新を防止）
        if now - self.last_update_time < 0.1 and current < self.total and not self.auto_refresh:
            return
        
        self.last_update_time = now
        
        # プログレスバーの更新
        progress_val = self.current / self.total
        self.progress_bar.progress(progress_val)
        
        # ステータステキストの更新
        status = f"{self.current}/{self.total} 完了"
        if self.message:
            status += f" - {self.message}"
        self.status_text.text(status)
        
        # 時間情報の更新
        self._update_time_info()
        
        # 完了チェック
        if self.current >= self.total:
            self.complete = True
            self.status_text.text(f"処理完了: {self.total}/{self.total}")
    
    def _update_time_info(self) -> None:
        """時間情報を更新する"""
        elapsed = time.time() - self.start_time
        
        # 経過時間の表示
        elapsed_str = self._format_time(elapsed)
        
        # 進捗が0より大きい場合のみ残り時間を計算
        if self.current > 0 and self.current < self.total:
            progress_ratio = self.current / self.total
            total_estimated = elapsed / progress_ratio
            remaining = total_estimated - elapsed
            
            # 残り時間の表示
            remaining_str = self._format_time(remaining)
            self.time_text.text(f"経過時間: {elapsed_str} | 残り時間: {remaining_str}")
        else:
            self.time_text.text(f"経過時間: {elapsed_str}")
    
    def _format_time(self, seconds: float) -> str:
        """
        時間を読みやすい形式にフォーマットする
        
        Args:
            seconds: 秒数
            
        Returns:
            フォーマットされた時間文字列
        """
        if seconds < 60:
            return f"{seconds:.1f}秒"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}分{secs:02d}秒"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}時間{minutes:02d}分"
    
    def reset(self) -> None:
        """プログレスバーをリセットする"""
        self.current = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time
        self.message = ""
        self.complete = False
        self.update(0, "リセットしました")
    
    def complete_with_message(self, message: str) -> None:
        """
        完了メッセージを表示して終了する
        
        Args:
            message: 完了メッセージ
        """
        self.current = self.total
        self.complete = True
        self.message = message
        self.update(self.total, message)


class SessionProgressTracker:
    """
    セッションステートを使用したプログレストラッカー
    
    Streamlitのセッションステートを使用して、ページリロード間でも進捗状況を保持します。
    """
    
    SESSION_KEY = "progress_tracker"
    
    @classmethod
    def get_progress(cls) -> Dict[str, Any]:
        """
        セッションからプログレス情報を取得する
        
        Returns:
            プログレス情報の辞書
        """
        if cls.SESSION_KEY not in st.session_state:
            st.session_state[cls.SESSION_KEY] = {
                "current": 0,
                "total": 0,
                "message": "",
                "start_time": time.time(),
                "complete": False
            }
        
        return st.session_state[cls.SESSION_KEY]
    
    @classmethod
    def update_progress(cls, current: int, total: int, message: str = "") -> None:
        """
        セッションのプログレス情報を更新する
        
        Args:
            current: 現在の処理数
            total: 処理の総数
            message: 表示するメッセージ
        """
        progress = cls.get_progress()
        progress["current"] = current
        progress["total"] = max(1, total)  # 0除算防止
        progress["message"] = message
        
        # 開始時間が設定されていない場合は設定
        if progress.get("start_time") is None:
            progress["start_time"] = time.time()
        
        # 完了フラグの設定
        if current >= total and total > 0:
            progress["complete"] = True
        
        st.session_state[cls.SESSION_KEY] = progress
    
    @classmethod
    def display_progress(cls) -> None:
        """セッションのプログレス情報を表示する"""
        progress = cls.get_progress()
        
        if progress["total"] <= 0:
            return
        
        current = progress["current"]
        total = progress["total"]
        message = progress["message"]
        start_time = progress["start_time"]
        
        # プログレスバーの表示
        progress_val = min(1.0, current / total)
        progress_bar = st.progress(progress_val)
        
        # 経過時間の計算
        elapsed = time.time() - start_time if start_time else 0
        
        # 経過時間の表示
        if elapsed < 60:
            elapsed_str = f"{elapsed:.1f}秒"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            secs = int(elapsed % 60)
            elapsed_str = f"{minutes}分{secs:02d}秒"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            elapsed_str = f"{hours}時間{minutes:02d}分"
        
        # 残り時間の計算と表示
        time_info = f"経過時間: {elapsed_str}"
        
        if current > 0 and current < total:
            progress_ratio = current / total
            total_estimated = elapsed / progress_ratio
            remaining = total_estimated - elapsed
            
            if remaining < 60:
                remaining_str = f"{remaining:.1f}秒"
            elif remaining < 3600:
                minutes = int(remaining // 60)
                secs = int(remaining % 60)
                remaining_str = f"{minutes}分{secs:02d}秒"
            else:
                hours = int(remaining // 3600)
                minutes = int((remaining % 3600) // 60)
                remaining_str = f"{hours}時間{minutes:02d}分"
            
            time_info += f" | 残り時間: {remaining_str}"
        
        # ステータスと時間情報の表示
        status_text = f"{current}/{total} 完了"
        if message:
            status_text += f" - {message}"
        
        st.text(status_text)
        st.text(time_info)
        
        # 完了メッセージ
        if progress["complete"]:
            st.success(f"処理完了: {total}/{total}")
    
    @classmethod
    def reset(cls) -> None:
        """プログレス情報をリセットする"""
        if cls.SESSION_KEY in st.session_state:
            del st.session_state[cls.SESSION_KEY]
