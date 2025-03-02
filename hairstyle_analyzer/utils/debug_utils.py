"""
デバッグユーティリティモジュール

このモジュールでは、アプリケーションのデバッグに役立つユーティリティ関数を提供します。
変数のインスペクション、パフォーマンス測定、コールスタック表示などの機能が含まれます。
"""

import inspect
import time
import functools
import logging
import json
import pprint
from typing import Any, Dict, List, Optional, Callable, TypeVar, Union
from datetime import datetime

# 関数の戻り値の型
T = TypeVar('T')


def inspect_variable(var: Any, name: Optional[str] = None, logger: Optional[logging.Logger] = None) -> None:
    """
    変数の詳細を出力する
    
    Args:
        var: 検査対象の変数
        name: 変数名（指定しない場合は自動取得を試みる）
        logger: 使用するロガー（指定しない場合はルートロガー）
    """
    # 変数名が指定されていない場合は呼び出し元のコードから取得を試みる
    if name is None:
        frames = inspect.getouterframes(inspect.currentframe())
        for frame in frames[1:]:  # 最初のフレームはこの関数自体なのでスキップ
            try:
                context = inspect.getframeinfo(frame.frame).code_context
                if context and 'inspect_variable(' in context[0]:
                    # 呼び出し行からパラメータ部分を抽出
                    line = context[0].strip()
                    start = line.find('inspect_variable(') + len('inspect_variable(')
                    param = line[start:line.find(',', start) if ',' in line[start:] else line.find(')', start)]
                    name = param.strip()
                    break
            except Exception:
                continue
    
    # ロガーの取得
    logger = logger or logging.getLogger()
    
    # 変数の基本情報
    var_type = type(var).__name__
    var_id = id(var)
    var_size = 0
    
    try:
        import sys
        var_size = sys.getsizeof(var)
    except (ImportError, TypeError):
        pass
    
    # 変数の内容
    try:
        # 簡単なデータ型の場合は値をそのまま表示
        if isinstance(var, (int, float, bool, str, type(None))):
            var_repr = repr(var)
        # リスト、タプル、セットの場合は要素数と内容を表示
        elif isinstance(var, (list, tuple, set)):
            var_repr = f"{var_type}({len(var)}): {pprint.pformat(var)}"
        # 辞書の場合はキー数と内容を表示
        elif isinstance(var, dict):
            var_repr = f"{var_type}({len(var)}): {pprint.pformat(var)}"
        # オブジェクトの場合は属性を表示
        elif hasattr(var, '__dict__'):
            var_repr = f"{var_type}: {pprint.pformat(var.__dict__)}"
        # その他の場合は文字列表現を表示
        else:
            var_repr = repr(var)
    except Exception as e:
        var_repr = f"<表示エラー: {str(e)}>"
    
    # 出力
    header = f"===== 変数検査: {name or '不明'} ====="
    footer = "=" * len(header)
    
    logger.debug(header)
    logger.debug(f"型: {var_type}")
    logger.debug(f"ID: {var_id}")
    logger.debug(f"サイズ: {var_size} バイト")
    logger.debug(f"内容:\n{var_repr}")
    logger.debug(footer)


def measure_time(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> Callable:
    """
    関数の実行時間を測定するデコレータ
    
    Args:
        logger: 使用するロガー（指定しない場合は呼び出し元のモジュールのロガー）
        level: ログレベル
        
    Returns:
        デコレータ関数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            nonlocal logger
            
            # ロガーが指定されていない場合は関数のモジュールのロガーを使用
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # 関数名を取得
            func_name = func.__name__
            
            # 開始時間を記録
            start_time = time.time()
            
            # 関数を実行
            result = func(*args, **kwargs)
            
            # 終了時間を記録
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # ミリ秒に変換
            
            # 実行時間をログに記録
            if execution_time < 1000:
                logger.log(level, f"{func_name} の実行時間: {execution_time:.2f}ms")
            else:
                logger.log(level, f"{func_name} の実行時間: {execution_time / 1000:.2f}秒")
            
            return result
        
        return wrapper
    
    return decorator


def async_measure_time(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> Callable:
    """
    非同期関数の実行時間を測定するデコレータ
    
    Args:
        logger: 使用するロガー（指定しない場合は呼び出し元のモジュールのロガー）
        level: ログレベル
        
    Returns:
        デコレータ関数
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal logger
            
            # ロガーが指定されていない場合は関数のモジュールのロガーを使用
            if logger is None:
                logger = logging.getLogger(func.__module__)
            
            # 関数名を取得
            func_name = func.__name__
            
            # 開始時間を記録
            start_time = time.time()
            
            # 関数を実行
            result = await func(*args, **kwargs)
            
            # 終了時間を記録
            end_time = time.time()
            execution_time = (end_time - start_time) * 1000  # ミリ秒に変換
            
            # 実行時間をログに記録
            if execution_time < 1000:
                logger.log(level, f"{func_name} の実行時間: {execution_time:.2f}ms")
            else:
                logger.log(level, f"{func_name} の実行時間: {execution_time / 1000:.2f}秒")
            
            return result
        
        return wrapper
    
    return decorator


def get_current_callstack(skip_frames: int = 0, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    現在のコールスタックを取得する
    
    Args:
        skip_frames: スキップするフレーム数
        limit: 取得するフレーム数の上限
        
    Returns:
        コールスタック情報のリスト
    """
    frames = inspect.getouterframes(inspect.currentframe())
    
    # 最初のいくつかのフレームをスキップ（この関数自体など）
    frames = frames[1 + skip_frames:]
    
    # 上限が指定されている場合は制限
    if limit is not None:
        frames = frames[:limit]
    
    # フレーム情報を整形
    result = []
    for frame in frames:
        frame_info = {
            'function': frame.function,
            'filename': frame.filename,
            'lineno': frame.lineno,
            'code_context': frame.code_context[0].strip() if frame.code_context else None,
            'module': inspect.getmodule(frame.frame).__name__ if inspect.getmodule(frame.frame) else None
        }
        
        # ローカル変数も取得（オプション）
        # frame_info['locals'] = {k: str(v) for k, v in frame.frame.f_locals.items()}
        
        result.append(frame_info)
    
    return result


def print_callstack(skip_frames: int = 0, limit: Optional[int] = None, logger: Optional[logging.Logger] = None) -> None:
    """
    現在のコールスタックをログに出力する
    
    Args:
        skip_frames: スキップするフレーム数
        limit: 取得するフレーム数の上限
        logger: 使用するロガー（指定しない場合はルートロガー）
    """
    logger = logger or logging.getLogger()
    
    # コールスタックの取得
    call_stack = get_current_callstack(skip_frames + 1, limit)
    
    # 出力
    logger.debug("===== コールスタック =====")
    for i, frame in enumerate(call_stack):
        logger.debug(f"{i}: {frame['module']}.{frame['function']} ({frame['filename']}:{frame['lineno']})")
        if frame['code_context']:
            logger.debug(f"   {frame['code_context']}")
    logger.debug("=========================")


def log_dict_diff(old: Dict[str, Any], new: Dict[str, Any], logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> None:
    """
    2つの辞書の差分をログに出力する
    
    Args:
        old: 比較元の辞書
        new: 比較先の辞書
        logger: 使用するロガー（指定しない場合はルートロガー）
        level: ログレベル
    """
    logger = logger or logging.getLogger()
    
    # 追加されたキー
    added = set(new.keys()) - set(old.keys())
    
    # 削除されたキー
    removed = set(old.keys()) - set(new.keys())
    
    # 変更されたキー
    changed = {k for k in set(old.keys()) & set(new.keys()) if old[k] != new[k]}
    
    # 変更がない場合は早期リターン
    if not added and not removed and not changed:
        logger.log(level, "辞書に変更はありません")
        return
    
    # 出力
    logger.log(level, "===== 辞書の差分 =====")
    
    if added:
        logger.log(level, "追加されたキー:")
        for key in sorted(added):
            logger.log(level, f"+ {key}: {new[key]}")
    
    if removed:
        logger.log(level, "削除されたキー:")
        for key in sorted(removed):
            logger.log(level, f"- {key}: {old[key]}")
    
    if changed:
        logger.log(level, "変更されたキー:")
        for key in sorted(changed):
            logger.log(level, f"* {key}: {old[key]} -> {new[key]}")
    
    logger.log(level, "=====================")


def object_to_dict(obj: Any) -> Dict[str, Any]:
    """
    オブジェクトを辞書に変換する
    
    Args:
        obj: 変換対象のオブジェクト
        
    Returns:
        オブジェクトの属性を表す辞書
    """
    # 基本型の場合はそのまま返す
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    
    # リスト、タプルの場合は各要素を再帰的に変換
    if isinstance(obj, (list, tuple)):
        return [object_to_dict(item) for item in obj]
    
    # 辞書の場合は各値を再帰的に変換
    if isinstance(obj, dict):
        return {key: object_to_dict(value) for key, value in obj.items()}
    
    # オブジェクトの場合は__dict__属性を使用
    if hasattr(obj, '__dict__'):
        result = {}
        for key, value in obj.__dict__.items():
            if not key.startswith('_'):  # プライベート属性は除外
                result[key] = object_to_dict(value)
        return result
    
    # その他の場合は文字列表現を返す
    return str(obj)


def dump_object(obj: Any, logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> None:
    """
    オブジェクトの内容をログに出力する
    
    Args:
        obj: 出力対象のオブジェクト
        logger: 使用するロガー（指定しない場合はルートロガー）
        level: ログレベル
    """
    logger = logger or logging.getLogger()
    
    # オブジェクトを辞書に変換
    obj_dict = object_to_dict(obj)
    
    # 整形して出力
    obj_type = type(obj).__name__
    logger.log(level, f"===== オブジェクト ({obj_type}) =====")
    
    # JSONに変換して整形
    try:
        obj_json = json.dumps(obj_dict, indent=2, ensure_ascii=False)
        for line in obj_json.split('\n'):
            logger.log(level, line)
    except (TypeError, ValueError):
        # JSON変換に失敗した場合はpprint使用
        obj_str = pprint.pformat(obj_dict, indent=2)
        for line in obj_str.split('\n'):
            logger.log(level, line)
    
    logger.log(level, "=============================")


class PerformanceMonitor:
    """パフォーマンスをモニタリングするクラス"""
    
    def __init__(self, name: str, logger: Optional[logging.Logger] = None, level: int = logging.DEBUG):
        """
        初期化
        
        Args:
            name: モニターの名前
            logger: 使用するロガー（指定しない場合はルートロガー）
            level: ログレベル
        """
        self.name = name
        self.logger = logger or logging.getLogger()
        self.level = level
        self.checkpoints = []
        self.start_time = None
    
    def start(self) -> None:
        """モニタリングを開始する"""
        self.start_time = time.time()
        self.checkpoints = [('start', self.start_time, 0.0)]
        self.logger.log(self.level, f"{self.name}: モニタリングを開始しました")
    
    def checkpoint(self, name: str) -> None:
        """
        チェックポイントを記録する
        
        Args:
            name: チェックポイント名
        """
        if self.start_time is None:
            self.start()
        
        current_time = time.time()
        elapsed = current_time - self.start_time
        last_checkpoint = self.checkpoints[-1][1]
        interval = current_time - last_checkpoint
        
        self.checkpoints.append((name, current_time, interval))
        self.logger.log(self.level, f"{self.name}: {name} - 経過: {elapsed:.3f}秒, 間隔: {interval:.3f}秒")
    
    def stop(self) -> Dict[str, Any]:
        """
        モニタリングを終了する
        
        Returns:
            モニタリング結果
        """
        if self.start_time is None:
            self.logger.warning(f"{self.name}: モニタリングが開始されていません")
            return {}
        
        self.checkpoint('end')
        total_time = self.checkpoints[-1][1] - self.start_time
        
        # 結果の作成
        result = {
            'name': self.name,
            'start_time': datetime.fromtimestamp(self.start_time).isoformat(),
            'total_time': total_time,
            'checkpoints': []
        }
        
        # チェックポイント情報の追加
        for i, (name, timestamp, interval) in enumerate(self.checkpoints):
            elapsed = timestamp - self.start_time
            percent = (elapsed / total_time) * 100 if total_time > 0 else 0
            
            result['checkpoints'].append({
                'name': name,
                'elapsed': elapsed,
                'interval': interval,
                'percent': percent
            })
        
        # 結果のサマリー出力
        self.logger.log(self.level, f"{self.name}: モニタリング完了 - 合計時間: {total_time:.3f}秒")
        self.logger.log(self.level, "チェックポイント:")
        
        for cp in result['checkpoints']:
            if cp['name'] != 'start':
                self.logger.log(self.level, f"- {cp['name']}: {cp['elapsed']:.3f}秒 ({cp['percent']:.1f}%) - 間隔: {cp['interval']:.3f}秒")
        
        return result
    
    def __enter__(self):
        """コンテキストマネージャーのエントリーポイント"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーの終了処理"""
        self.stop()
