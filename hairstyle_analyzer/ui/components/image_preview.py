"""
画像プレビューコンポーネントモジュール

このモジュールでは、アップロードされた画像のプレビューを表示するためのコンポーネントを提供します。
グリッドレイアウト、サムネイル表示、選択機能などが含まれます。
"""

import logging
import streamlit as st
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, Union
import base64
from PIL import Image
import io

from ...utils.image_utils import is_valid_image, resize_image


class ImagePreviewComponent:
    """
    画像プレビュー表示コンポーネント
    
    アップロードされた画像のサムネイルをグリッド表示し、選択機能を提供します。
    """
    
    def __init__(self, max_height: int = 200, columns: int = 3):
        """
        初期化
        
        Args:
            max_height: サムネイルの最大高さ（ピクセル）
            columns: グリッドの列数
        """
        self.logger = logging.getLogger(__name__)
        self.max_height = max_height
        self.columns = columns
    
    def display_images(self, 
                     images: List[Union[Path, bytes, Image.Image]],
                     captions: Optional[List[str]] = None,
                     on_select: Optional[Callable[[int], None]] = None) -> Optional[int]:
        """
        画像をグリッド表示します
        
        Args:
            images: 表示する画像のリスト（パス、バイト、PIL.Imageのいずれか）
            captions: 各画像のキャプション（オプション）
            on_select: 画像選択時のコールバック関数（オプション）
            
        Returns:
            選択された画像のインデックス、または選択がない場合はNone
        """
        if not images:
            st.info("表示する画像がありません。")
            return None
        
        # キャプションが指定されていない場合はデフォルト値を使用
        if captions is None:
            captions = [f"画像 {i+1}" for i in range(len(images))]
        elif len(captions) < len(images):
            # キャプションが足りない場合は拡張
            captions.extend([f"画像 {i+1}" for i in range(len(captions), len(images))])
        
        # カラムを作成
        selected_index = None
        cols = st.columns(self.columns)
        
        for i, (image, caption) in enumerate(zip(images, captions)):
            col_index = i % self.columns
            
            with cols[col_index]:
                # 画像を適切な形式に変換
                pil_image = self._get_pil_image(image)
                
                if pil_image:
                    # 画像をリサイズ（アスペクト比維持）
                    img_width, img_height = pil_image.size
                    ratio = self.max_height / img_height if img_height > self.max_height else 1
                    new_size = (int(img_width * ratio), int(img_height * ratio))
                    resized_image = pil_image.resize(new_size, Image.LANCZOS)
                    
                    # 画像を表示
                    st.image(resized_image, caption=caption, use_container_width=True)
                    
                    # 選択ボタン
                    if on_select:
                        if st.button(f"選択 #{i+1}", key=f"select_img_{i}"):
                            selected_index = i
                            on_select(i)
                else:
                    st.error(f"画像 #{i+1} を表示できません")
        
        return selected_index

    def display_single_image(self, 
                          image: Union[Path, bytes, Image.Image],
                          caption: Optional[str] = None,
                          use_full_width: bool = False,
                          max_width: Optional[int] = None) -> None:
        """
        単一の画像を表示します
        
        Args:
            image: 表示する画像（パス、バイト、PIL.Imageのいずれか）
            caption: 画像のキャプション（オプション）
            use_full_width: 画面幅いっぱいに表示するかどうか
            max_width: 表示する最大幅（ピクセル）（オプション）
        """
        # 画像を適切な形式に変換
        pil_image = self._get_pil_image(image)
        
        if pil_image:
            # 最大幅が指定されていて、画像がそれより大きい場合はリサイズ
            if max_width:
                img_width, img_height = pil_image.size
                if img_width > max_width:
                    ratio = max_width / img_width
                    new_size = (max_width, int(img_height * ratio))
                    pil_image = pil_image.resize(new_size, Image.LANCZOS)
            
            # 画像を表示
            st.image(pil_image, caption=caption, use_container_width=use_full_width)
        else:
            st.error("画像を表示できません")
    
    def _get_pil_image(self, image: Union[Path, bytes, Image.Image]) -> Optional[Image.Image]:
        """
        様々な入力形式からPIL.Imageオブジェクトを取得します
        
        Args:
            image: 変換する画像（パス、バイト、PIL.Imageのいずれか）
            
        Returns:
            PILイメージオブジェクト、または変換できない場合はNone
        """
        try:
            if isinstance(image, Path):
                # パスからの読み込み
                if is_valid_image(image):
                    return Image.open(image)
                else:
                    self.logger.warning(f"無効な画像ファイル: {image}")
                    return None
                    
            elif isinstance(image, bytes):
                # バイト列からの読み込み
                return Image.open(io.BytesIO(image))
                
            elif isinstance(image, Image.Image):
                # すでにPIL.Imageの場合はそのまま返す
                return image
                
            else:
                self.logger.warning(f"サポートされていない画像タイプ: {type(image)}")
                return None
                
        except Exception as e:
            self.logger.error(f"画像変換エラー: {str(e)}")
            return None

    def create_gallery(self, images: List[Union[Path, bytes, Image.Image]], 
                     captions: Optional[List[str]] = None,
                     thumbnail_height: int = 100,
                     gallery_height: int = 400) -> None:
        """
        クリックで拡大表示できるギャラリービューを作成します
        
        Args:
            images: 表示する画像のリスト（パス、バイト、PIL.Imageのいずれか）
            captions: 各画像のキャプション（オプション）
            thumbnail_height: サムネイルの高さ（ピクセル）
            gallery_height: ギャラリービューの高さ（ピクセル）
        """
        if not images:
            st.info("表示する画像がありません。")
            return
        
        # キャプションが指定されていない場合はデフォルト値を使用
        if captions is None:
            captions = [f"画像 {i+1}" for i in range(len(images))]
        
        # セッションステートに選択中の画像インデックスを保存
        if 'selected_image_index' not in st.session_state:
            st.session_state.selected_image_index = 0
        
        # メイン画像表示エリア
        selected_idx = st.session_state.selected_image_index
        if 0 <= selected_idx < len(images):
            selected_image = self._get_pil_image(images[selected_idx])
            if selected_image:
                st.image(selected_image, caption=captions[selected_idx], use_container_width=True)
            else:
                st.error("選択された画像を表示できません")
        
        # サムネイルエリア (スクロール可能)
        st.write("##### すべての画像")
        
        # スクロール可能なコンテナを作成
        thumbnail_container = st.container()
        with thumbnail_container:
            # CSS適用
            st.markdown(f"""
                <style>
                    .thumbnail-container {{
                        display: flex;
                        overflow-x: auto;
                        padding: 10px 0;
                        max-height: {thumbnail_height + 50}px;
                    }}
                    .thumbnail {{
                        margin-right: 10px;
                        cursor: pointer;
                        border: 2px solid transparent;
                    }}
                    .thumbnail.selected {{
                        border: 2px solid #1E88E5;
                    }}
                </style>
                """, unsafe_allow_html=True)
            
            # サムネイル行を作成
            cols = st.columns(min(len(images), 10))
            
            for i, (image, caption) in enumerate(zip(images, captions)):
                col_index = i % len(cols)
                
                with cols[col_index]:
                    # 画像を適切な形式に変換
                    pil_image = self._get_pil_image(image)
                    
                    if pil_image:
                        # サムネイルをリサイズ
                        img_width, img_height = pil_image.size
                        ratio = thumbnail_height / img_height
                        new_size = (int(img_width * ratio), thumbnail_height)
                        thumb = pil_image.resize(new_size, Image.LANCZOS)
                        
                        # サムネイルを表示
                        st.image(thumb, caption=f"#{i+1}", use_container_width=False)
                        
                        # 選択ボタン
                        if st.button(f"表示", key=f"thumb_{i}"):
                            st.session_state.selected_image_index = i
                            st.experimental_rerun()
