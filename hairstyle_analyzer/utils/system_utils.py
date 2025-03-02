"""
システムユーティリティモジュール

このモジュールでは、システムリソースの監視や最適化に関するユーティリティ関数を提供します。
メモリ使用量、CPU使用率、最適なバッチサイズの計算などの機能が含まれます。
"""

import os
import platform
import logging
from typing import Dict, Any, Tuple, Optional

# psutilをインポート
try:
    import psutil
    has_psutil = True
except ImportError:
    has_psutil = False
    logging.warning("psutilがインストールされていません。システムリソース監視機能が制限されます。")


def get_system_info() -> Dict[str, Any]:
    """
    システム情報を取得する
    
    Returns:
        システム情報を含む辞書
    """
    info = {
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'processor': platform.processor()
    }
    
    # psutilが利用可能な場合は詳細情報を追加
    if has_psutil:
        memory = psutil.virtual_memory()
        info.update({
            'memory_total': memory.total,
            'memory_available': memory.available,
            'cpu_count_physical': psutil.cpu_count(logical=False),
            'cpu_count_logical': psutil.cpu_count(logical=True)
        })
    
    return info


def get_memory_usage() -> Dict[str, Any]:
    """
    メモリ使用状況を取得する
    
    Returns:
        メモリ使用状況を含む辞書
    """
    if not has_psutil:
        return {'error': 'psutilがインストールされていません'}
    
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        
        return {
            'rss': memory_info.rss,  # 物理メモリ使用量
            'vms': memory_info.vms,  # 仮想メモリ使用量
            'percent': process.memory_percent()  # 全体に対する割合
        }
    except Exception as e:
        logging.warning(f"メモリ使用状況の取得エラー: {e}")
        return {'error': str(e)}


def get_cpu_usage() -> Dict[str, Any]:
    """
    CPU使用状況を取得する
    
    Returns:
        CPU使用状況を含む辞書
    """
    if not has_psutil:
        return {'error': 'psutilがインストールされていません'}
    
    try:
        process = psutil.Process(os.getpid())
        
        return {
            'percent': process.cpu_percent(interval=0.1),  # プロセスのCPU使用率
            'system_percent': psutil.cpu_percent(interval=0.1)  # システム全体のCPU使用率
        }
    except Exception as e:
        logging.warning(f"CPU使用状況の取得エラー: {e}")
        return {'error': str(e)}


def calculate_optimal_batch_size(
    memory_per_item_mb: int = 5,
    max_memory_percent: float = 70.0,
    min_batch_size: int = 1,
    max_batch_size: int = 20,
    cpu_factor: float = 0.5
) -> int:
    """
    システムリソースに基づいて最適なバッチサイズを計算する
    
    Args:
        memory_per_item_mb: 1アイテムあたりの推定メモリ使用量（MB）
        max_memory_percent: 使用可能な最大メモリ使用率（%）
        min_batch_size: 最小バッチサイズ
        max_batch_size: 最大バッチサイズ
        cpu_factor: CPUコア数に対する倍率
        
    Returns:
        計算された最適なバッチサイズ
    """
    if not has_psutil:
        # psutilが利用できない場合はデフォルト値を返す
        logging.warning("psutilがインストールされていないため、デフォルトのバッチサイズを使用します")
        return max(min_batch_size, min(5, max_batch_size))
    
    try:
        # 利用可能なメモリの計算
        memory = psutil.virtual_memory()
        available_memory_mb = memory.available / (1024 * 1024)
        
        # メモリベースのバッチサイズを計算
        # 利用可能なメモリの max_memory_percent% までを使用
        usable_memory_mb = available_memory_mb * (max_memory_percent / 100)
        memory_based_size = int(usable_memory_mb / memory_per_item_mb)
        
        # CPUベースのバッチサイズを計算
        cpu_count = psutil.cpu_count(logical=False) or 1
        cpu_based_size = int(cpu_count * cpu_factor)
        
        # 最小と最大の範囲内で、メモリベースとCPUベースの小さい方を選択
        optimal_size = min(memory_based_size, cpu_based_size)
        optimal_size = max(min_batch_size, min(optimal_size, max_batch_size))
        
        logging.info(
            f"最適なバッチサイズを計算: {optimal_size} "
            f"(メモリベース: {memory_based_size}, CPUベース: {cpu_based_size})"
        )
        
        return optimal_size
    except Exception as e:
        logging.warning(f"最適なバッチサイズの計算エラー: {e}")
        return max(min_batch_size, min(5, max_batch_size))


def create_directory_if_not_exists(directory_path: str) -> Tuple[bool, Optional[str]]:
    """
    ディレクトリが存在しない場合は作成する
    
    Args:
        directory_path: ディレクトリのパス
        
    Returns:
        (成功したかどうか, エラーメッセージ)
    """
    try:
        os.makedirs(directory_path, exist_ok=True)
        return True, None
    except Exception as e:
        return False, str(e)


def ensure_writable(file_path: str) -> Tuple[bool, Optional[str]]:
    """
    ファイルパスが書き込み可能かどうかを確認する
    
    Args:
        file_path: チェックするファイルパス
        
    Returns:
        (書き込み可能かどうか, エラーメッセージ)
    """
    # ディレクトリの存在確認
    directory = os.path.dirname(file_path)
    if directory and not os.path.exists(directory):
        success, error = create_directory_if_not_exists(directory)
        if not success:
            return False, f"ディレクトリの作成に失敗: {error}"
    
    # ファイルが既に存在する場合は書き込み権限を確認
    if os.path.exists(file_path):
        if not os.access(file_path, os.W_OK):
            return False, "ファイルに書き込み権限がありません"
    # ファイルが存在しない場合はディレクトリの書き込み権限を確認
    elif not os.access(directory or '.', os.W_OK):
        return False, "ディレクトリに書き込み権限がありません"
    
    return True, None
