"""
画像処理ユーティリティモジュール

このモジュールでは、画像処理に関するユーティリティ関数を提供します。
画像のロード、エンコード、リサイズ、検証などの機能が含まれます。
"""

import os
import base64
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Union, Any
import imghdr

# Pillowをインポート
try:
    from PIL import Image
except ImportError:
    logging.warning("Pillowがインストールされていません。画像処理機能が制限されます。")


def is_valid_image(file_path: Union[str, Path]) -> bool:
    """
    与えられたファイルが有効な画像かどうかを判定する
    
    Args:
        file_path: 画像ファイルのパス
        
    Returns:
        有効な画像の場合はTrue、そうでない場合はFalse
    """
    file_path = Path(file_path)
    
    # ファイルが存在するか
    if not file_path.exists():
        logging.warning(f"ファイルが存在しません: {file_path}")
        return False
    
    # 拡張子のチェック
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    if file_path.suffix.lower() not in valid_extensions:
        logging.warning(f"サポートされていない拡張子: {file_path.suffix}")
        return False
    
    # 画像形式のチェック
    try:
        image_type = imghdr.what(file_path)
        return image_type is not None
    except Exception as e:
        logging.warning(f"画像形式の検証エラー: {e}")
        return False


def encode_image(file_path: Union[str, Path]) -> str:
    """
    画像をBase64でエンコードする
    
    Args:
        file_path: 画像ファイルのパス
        
    Returns:
        Base64エンコードされた画像データ
        
    Raises:
        ValueError: 画像のエンコードに失敗した場合
    """
    file_path = Path(file_path)
    
    # 画像の検証
    if not is_valid_image(file_path):
        raise ValueError(f"無効な画像ファイル: {file_path}")
    
    try:
        with open(file_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise ValueError(f"画像のエンコードに失敗: {e}")


def get_image_size(file_path: Union[str, Path]) -> Tuple[int, int]:
    """
    画像のサイズを取得する
    
    Args:
        file_path: 画像ファイルのパス
        
    Returns:
        (幅, 高さ)のタプル
        
    Raises:
        ValueError: 画像サイズの取得に失敗した場合
    """
    file_path = Path(file_path)
    
    try:
        with Image.open(file_path) as img:
            return img.size
    except Exception as e:
        raise ValueError(f"画像サイズの取得に失敗: {e}")


def resize_image(file_path: Union[str, Path], max_size: int = 1024, output_path: Optional[Union[str, Path]] = None) -> Path:
    """
    画像をリサイズする
    
    Args:
        file_path: 画像ファイルのパス
        max_size: 最大サイズ（幅または高さの最大値）
        output_path: 出力先のパス（指定しない場合は入力ファイルを上書き）
        
    Returns:
        リサイズされた画像のパス
        
    Raises:
        ValueError: 画像のリサイズに失敗した場合
    """
    file_path = Path(file_path)
    output_path = Path(output_path) if output_path else file_path
    
    try:
        with Image.open(file_path) as img:
            # 現在のサイズを取得
            width, height = img.size
            
            # リサイズが必要かどうかを判定
            if width <= max_size and height <= max_size:
                # リサイズ不要の場合は、output_pathが入力と異なる場合のみコピー
                if output_path != file_path:
                    import shutil
                    shutil.copy2(file_path, output_path)
                return output_path
            
            # アスペクト比を維持したままリサイズ
            if width > height:
                new_width = max_size
                new_height = int(height * (max_size / width))
            else:
                new_height = max_size
                new_width = int(width * (max_size / height))
            
            # リサイズ
            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
            
            # 保存
            resized_img.save(output_path, quality=90)
            
            return output_path
    except Exception as e:
        raise ValueError(f"画像のリサイズに失敗: {e}")


def get_image_format(file_path: Union[str, Path]) -> str:
    """
    画像の形式を取得する
    
    Args:
        file_path: 画像ファイルのパス
        
    Returns:
        画像形式（'JPEG', 'PNG'など）
        
    Raises:
        ValueError: 画像形式の取得に失敗した場合
    """
    file_path = Path(file_path)
    
    try:
        with Image.open(file_path) as img:
            return img.format
    except Exception as e:
        raise ValueError(f"画像形式の取得に失敗: {e}")


def get_images_from_directory(directory: Union[str, Path], recursive: bool = False) -> List[Path]:
    """
    ディレクトリ内の画像ファイル一覧を取得する
    
    Args:
        directory: 画像を検索するディレクトリ
        recursive: サブディレクトリも検索するかどうか
        
    Returns:
        画像ファイルのパスリスト
    """
    directory = Path(directory)
    
    if not directory.exists() or not directory.is_dir():
        logging.warning(f"ディレクトリが存在しません: {directory}")
        return []
    
    image_paths = []
    
    # 画像拡張子の定義
    valid_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp'}
    
    # ディレクトリ内のファイルを検索
    if recursive:
        # 再帰的に検索
        for root, _, files in os.walk(directory):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in valid_extensions and is_valid_image(file_path):
                    image_paths.append(file_path)
    else:
        # 現在のディレクトリのみ検索
        for file_path in directory.iterdir():
            if file_path.is_file() and file_path.suffix.lower() in valid_extensions and is_valid_image(file_path):
                image_paths.append(file_path)
    
    return sorted(image_paths)


def get_images_matching_pattern(directory: Union[str, Path], pattern: str = "styleimg (*).png") -> List[Path]:
    """
    ディレクトリ内のパターンにマッチする画像ファイル一覧を取得する
    
    Args:
        directory: 画像を検索するディレクトリ
        pattern: ファイル名パターン（ワイルドカード * を使用可能）
        
    Returns:
        画像ファイルのパスリスト
    """
    import fnmatch
    directory = Path(directory)
    
    if not directory.exists() or not directory.is_dir():
        logging.warning(f"ディレクトリが存在しません: {directory}")
        return []
    
    # ディレクトリ内のファイルをリスト化
    all_files = list(directory.iterdir())
    
    # パターンにマッチするファイルをフィルタリング
    matched_files = [
        path for path in all_files
        if path.is_file() and fnmatch.fnmatch(path.name, pattern) and is_valid_image(path)
    ]
    
    # 数値でソート（例: "styleimg (1).png", "styleimg (2).png", ...）
    def extract_number(path):
        import re
        match = re.search(r'\((\d+)\)', path.name)
        return int(match.group(1)) if match else 0
    
    return sorted(matched_files, key=extract_number)
