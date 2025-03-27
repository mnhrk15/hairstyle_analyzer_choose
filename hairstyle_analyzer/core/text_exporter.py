"""
テキスト出力モジュール

このモジュールでは、処理結果をテキスト形式で出力するための機能を提供します。
テキスト生成の基本機能、カスタムフォーマット設定、データ変換などの機能が含まれます。
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime

from ..data.models import ProcessResult, TextConfig
from ..data.interfaces import TextExporterProtocol, ProcessResultProtocol
from ..utils.errors import AppError, with_error_handling


class TextExportError(AppError):
    """テキスト出力関連のエラー"""
    
    def __init__(self, message: str, output_path: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """
        初期化
        
        Args:
            message: エラーメッセージ
            output_path: 出力パス（オプション）
            details: 追加の詳細情報（オプション）
        """
        details = details or {}
        if output_path:
            details['output_path'] = output_path
        super().__init__(message, details)
        self.output_path = output_path


class TextExporter(TextExporterProtocol):
    """
    テキスト出力クラス
    
    処理結果をテキスト形式で出力します。
    テキスト生成の基本機能、カスタムフォーマット設定、データ変換などの機能が含まれます。
    """
    
    def __init__(self, config: TextConfig, filename_mapping: Dict[str, str] = None):
        """
        初期化
        
        Args:
            config: テキスト出力設定
            filename_mapping: ファイル名のマッピング辞書（オプション）
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self.filename_mapping = filename_mapping or {}
    
    @with_error_handling(TextExportError, "テキスト出力処理でエラーが発生しました")
    def export(self, results: List[ProcessResultProtocol], output_path: Union[str, Path]) -> Path:
        """
        処理結果をテキストファイルに出力します。
        
        Args:
            results: 処理結果のリスト
            output_path: 出力ファイルのパス
            
        Returns:
            エクスポートされたファイルのパス
            
        Raises:
            TextExportError: テキスト出力処理でエラーが発生した場合
        """
        self.logger.info(f"テキスト出力開始: 結果数={len(results)}, 出力先={output_path}")
        
        # 文字列パスをPathオブジェクトに変換
        if isinstance(output_path, str):
            output_path = Path(output_path)
        
        # 出力ディレクトリが存在しない場合は作成
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 既存ファイルのバックアップ
        if output_path.exists():
            backup_path = self._create_backup(output_path)
            self.logger.info(f"既存ファイルをバックアップしました: {backup_path}")
        
        # テキストコンテンツの生成
        text_content = self.get_text_content(results)
        
        # ファイルに書き込み
        try:
            with open(output_path, "w", encoding=self.config.encoding) as f:
                f.write(text_content)
            self.logger.info(f"テキストファイルを保存しました: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"テキストファイルの保存エラー: {e}")
            raise TextExportError(f"テキストファイルの保存に失敗しました: {str(e)}", 
                                output_path=str(output_path)) from e
    
    @with_error_handling(TextExportError, "テキストデータの生成でエラーが発生しました")
    def get_text_content(self, results: List[ProcessResultProtocol]) -> str:
        """
        処理結果のテキストデータを取得します。
        
        Args:
            results: 処理結果のリスト
            
        Returns:
            テキストデータ
            
        Raises:
            TextExportError: テキスト生成処理でエラーが発生した場合
        """
        self.logger.info(f"テキストデータ生成開始: 結果数={len(results)}")
        
        # 結果ごとにテキストを生成して結合
        text_parts = []
        
        for result in results:
            try:
                # 個別の結果からテキストを生成
                result_text = self._format_result(result)
                text_parts.append(result_text)
            except Exception as e:
                self.logger.error(f"結果のテキスト形式化エラー: {e}")
                # エラーが発生しても続行し、エラーメッセージを含める
                text_parts.append(f"[エラー: {str(e)}]")
        
        # すべての結果を結合
        text_content = self.config.newline.join(text_parts)
        
        self.logger.info(f"テキストデータを生成しました: {len(text_content)} 文字")
        return text_content
    
    def _create_backup(self, file_path: Path) -> Path:
        """
        ファイルのバックアップを作成します。
        
        Args:
            file_path: バックアップするファイルのパス
            
        Returns:
            バックアップファイルのパス
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = file_path.with_name(f"{file_path.stem}_{timestamp}_backup{file_path.suffix}")
        
        # ファイルをコピー
        import shutil
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    def _format_result(self, result: ProcessResultProtocol) -> str:
        """
        結果を文字列にフォーマットする
        
        Args:
            result: 処理結果
        
        Returns:
            フォーマットされた文字列
        """
        try:
            # 画像名の取得と変換
            if isinstance(result, dict):
                image_name = result.get('image_name', '')
            else:
                image_name = getattr(result, 'image_name', '')

            # ファイル名の変換（小文字で比較）
            image_name_lower = image_name.lower()
            if image_name_lower in self.filename_mapping:
                image_name = self.filename_mapping[image_name_lower]
                self.logger.info(f"ファイル名を変換: {image_name_lower} -> {image_name}")

            # その他の情報を取得
            if isinstance(result, dict):
                stylist_name = result.get('selected_stylist', {}).get('name', '')
                comment = result.get('selected_template', {}).get('comment', '')
                title = result.get('selected_template', {}).get('title', '')
                sex = result.get('attribute_analysis', {}).get('sex', '')
                length = result.get('attribute_analysis', {}).get('length', '')
                menu = result.get('selected_template', {}).get('menu', '')
                coupon_name = result.get('selected_coupon', {}).get('name', '')
                hashtag = result.get('selected_template', {}).get('hashtag', '')
            else:
                stylist_name = getattr(result.selected_stylist, 'name', '')
                comment = getattr(result.selected_template, 'comment', '')
                title = getattr(result.selected_template, 'title', '')
                sex = getattr(result.attribute_analysis, 'sex', '')
                length = getattr(result.attribute_analysis, 'length', '')
                menu = getattr(result.selected_template, 'menu', '')
                coupon_name = getattr(result.selected_coupon, 'name', '')
                hashtag = getattr(result.selected_template, 'hashtag', '')

            # フォーマットテンプレートに値を埋め込み
            formatted_text = self.config.format_template.format(
                image_name=image_name,
                stylist_name=stylist_name,
                comment=comment,
                title=title,
                sex=sex,
                length=length,
                menu=menu,
                coupon_name=coupon_name,
                hashtag=hashtag
            )
            
            return formatted_text
        except Exception as e:
            self.logger.error(f"結果のテキスト形式化エラー: {e}")
            return f"[エラー: {str(e)}]" 