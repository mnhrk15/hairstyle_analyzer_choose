"""
ファイルアップロードコンポーネントモジュール

このモジュールでは、Streamlitで使用するファイルアップロードコンポーネントを提供します。
画像ファイルのアップロード、プレビュー表示、検証などの機能が含まれます。
"""

import os
import tempfile
from typing import List, Dict, Any, Optional, Tuple, Set
from pathlib import Path

import streamlit as st
from PIL import Image
import imghdr

from ...utils.image_utils import is_valid_image


class FileUploader:
    """
    ファイルアップロードコンポーネント
    
    画像ファイルのアップロードとプレビュー表示を行うコンポーネントです。
    """
    
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    SESSION_KEY_UPLOADED = "uploaded_files"
    SESSION_KEY_PATHS = "temp_image_paths"
    
    def __init__(self, title: str = "画像ファイルをアップロード", key: str = "image_uploader"):
        """
        初期化
        
        Args:
            title: アップロードコンポーネントのタイトル
            key: Streamlitウィジェットのユニークキー
        """
        self.title = title
        self.key = key
        self.uploaded_files = []
        self.temp_image_paths = []
    
    def render(self) -> List[st.runtime.uploaded_file_manager.UploadedFile]:
        """
        アップロードコンポーネントを表示し、アップロードされたファイルを返す
        
        Returns:
            アップロードされたファイルのリスト
        """
        # ファイルアップローダーの表示
        uploaded_files = st.file_uploader(
            self.title,
            type=["jpg", "jpeg", "png"],
            accept_multiple_files=True,
            key=self.key,
            help="JPG, JPEG, PNG形式の画像ファイルをアップロードしてください。"
        )
        
        # セッションに保存
        self.uploaded_files = uploaded_files or []
        
        # セッションのクリーンアップ
        if self.SESSION_KEY_PATHS in st.session_state:
            # 前回の一時ファイルを削除
            for path in st.session_state[self.SESSION_KEY_PATHS]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception as e:
                    st.warning(f"一時ファイルの削除中にエラーが発生しました: {str(e)}")
        
        # セッションを更新
        st.session_state[self.SESSION_KEY_UPLOADED] = self.uploaded_files
        st.session_state[self.SESSION_KEY_PATHS] = []
        
        return self.uploaded_files
    
    def save_to_temp(self) -> List[Path]:
        """
        アップロードされたファイルを一時ディレクトリに保存する
        
        Returns:
            一時ファイルのパスリスト
        """
        temp_paths = []
        
        # 一時ディレクトリの作成
        temp_dir = Path(tempfile.gettempdir()) / "hairstyle_analyzer"
        temp_dir.mkdir(exist_ok=True)
        
        for uploaded_file in self.uploaded_files:
            # 一時ファイルパスの作成
            temp_path = temp_dir / uploaded_file.name
            
            # ファイル保存
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # 画像の検証
            if is_valid_image(temp_path):
                temp_paths.append(temp_path)
                st.session_state[self.SESSION_KEY_PATHS].append(str(temp_path))
            else:
                st.warning(f"無効な画像ファイル: {uploaded_file.name} - スキップします")
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
        
        # 結果の保存
        self.temp_image_paths = temp_paths
        
        return temp_paths
    
    def display_previews(self, max_previews: int = 4, columns: int = 4):
        """
        アップロードされた画像のプレビューを表示する
        
        Args:
            max_previews: 表示する最大プレビュー数
            columns: 表示カラム数
        """
        if not self.uploaded_files:
            return
        
        # プレビュー表示用のカラムを作成
        num_previews = min(len(self.uploaded_files), max_previews)
        num_columns = min(columns, num_previews)
        cols = st.columns(num_columns)
        
        # プレビュー表示
        for i, uploaded_file in enumerate(self.uploaded_files[:max_previews]):
            with cols[i % num_columns]:
                try:
                    # 画像のプレビュー表示
                    image = Image.open(uploaded_file)
                    st.image(image, width=150, caption=uploaded_file.name)
                except Exception as e:
                    st.error(f"画像の読み込みエラー: {uploaded_file.name}")
        
        # 残りの画像数を表示
        if len(self.uploaded_files) > max_previews:
            st.write(f"他 {len(self.uploaded_files) - max_previews}枚...")
    
    def get_image_info(self) -> List[Dict[str, Any]]:
        """
        アップロードされた画像の情報を取得する
        
        Returns:
            画像情報のリスト
        """
        image_info = []
        
        for uploaded_file in self.uploaded_files:
            try:
                # 画像を開く
                image = Image.open(uploaded_file)
                
                # 情報を収集
                info = {
                    'filename': uploaded_file.name,
                    'size': uploaded_file.size,
                    'format': image.format,
                    'width': image.width,
                    'height': image.height,
                    'mode': image.mode
                }
                
                image_info.append(info)
            except Exception as e:
                # エラー情報を追加
                info = {
                    'filename': uploaded_file.name,
                    'size': uploaded_file.size,
                    'error': str(e)
                }
                image_info.append(info)
        
        return image_info
    
    @staticmethod
    def display_image_grid(images: List[Path], columns: int = 4, width: int = 150):
        """
        画像をグリッド表示する
        
        Args:
            images: 画像パスのリスト
            columns: 表示カラム数
            width: 画像の幅
        """
        if not images:
            return
        
        # グリッド表示用のカラムを作成
        num_columns = min(columns, len(images))
        cols = st.columns(num_columns)
        
        # グリッド表示
        for i, image_path in enumerate(images):
            with cols[i % num_columns]:
                try:
                    # 画像の表示
                    image = Image.open(image_path)
                    st.image(image, width=width, caption=image_path.name)
                except Exception as e:
                    st.error(f"画像の読み込みエラー: {image_path.name}")
    
    @staticmethod
    def cleanup_temp_files():
        """一時ファイルをクリーンアップする"""
        if FileUploader.SESSION_KEY_PATHS in st.session_state:
            # 一時ファイルを削除
            for path in st.session_state[FileUploader.SESSION_KEY_PATHS]:
                try:
                    if os.path.exists(path):
                        os.unlink(path)
                except Exception as e:
                    st.warning(f"一時ファイルの削除中にエラーが発生しました: {str(e)}")
            
            # セッションをクリア
            st.session_state[FileUploader.SESSION_KEY_PATHS] = []


class ImageSelector:
    """
    画像選択コンポーネント
    
    アップロードした画像から選択するコンポーネントです。
    """
    
    SESSION_KEY = "selected_images"
    
    def __init__(self, key: str = "image_selector"):
        """
        初期化
        
        Args:
            key: Streamlitウィジェットのユニークキー
        """
        self.key = key
        self.selected_indices = []
    
    def render(self, images: List[Any], use_checkbox: bool = True) -> List[int]:
        """
        画像選択コンポーネントを表示する
        
        Args:
            images: 画像のリスト
            use_checkbox: チェックボックスを使用するかどうか
            
        Returns:
            選択された画像のインデックスリスト
        """
        if not images:
            return []
        
        selected_indices = []
        
        if use_checkbox:
            # チェックボックスを使用した選択
            for i, image in enumerate(images):
                # 画像名の取得
                image_name = getattr(image, 'name', f"画像 {i+1}")
                
                # チェックボックスの表示
                selected = st.checkbox(
                    f"選択: {image_name}",
                    value=False,
                    key=f"{self.key}_{i}"
                )
                
                if selected:
                    selected_indices.append(i)
        else:
            # マルチセレクトを使用した選択
            image_names = [getattr(image, 'name', f"画像 {i+1}") for i, image in enumerate(images)]
            
            selected_names = st.multiselect(
                "画像を選択してください",
                options=image_names,
                key=self.key
            )
            
            # 選択されたインデックスを取得
            selected_indices = [i for i, name in enumerate(image_names) if name in selected_names]
        
        # セッションに保存
        self.selected_indices = selected_indices
        st.session_state[self.SESSION_KEY] = selected_indices
        
        return selected_indices
    
    def get_selected_images(self, images: List[Any]) -> List[Any]:
        """
        選択された画像を取得する
        
        Args:
            images: 画像のリスト
            
        Returns:
            選択された画像のリスト
        """
        return [images[i] for i in self.selected_indices if i < len(images)]
