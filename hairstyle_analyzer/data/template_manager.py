"""
テンプレート管理モジュール

このモジュールでは、ヘアスタイルのテンプレート情報の読み込み、管理、検索を行います。
CSVファイルからテンプレートを読み込み、最適なテンプレートをマッチングする機能を提供します。
"""

import csv
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union, Any
import difflib
from collections import defaultdict

import pandas as pd
from pydantic import ValidationError

from .models import Template, StyleAnalysis
from .interfaces import TemplateManagerProtocol, StyleAnalysisProtocol
from ..utils.errors import TemplateError, with_error_handling


class TemplateManager(TemplateManagerProtocol):
    """テンプレート管理クラス
    
    CSVファイルからテンプレートを読み込み、カテゴリーごとに整理して、
    スタイル分析結果に基づいて最適なテンプレートを検索する機能を提供します。
    """
    
    # 必須のCSVヘッダーフィールド
    REQUIRED_FIELDS = {'category', 'title', 'menu', 'comment', 'hashtag'}
    
    def __init__(self, template_file_path: Union[str, Path]):
        """
        初期化
        
        Args:
            template_file_path: テンプレートCSVファイルのパス
        """
        self.logger = logging.getLogger(__name__)
        self.template_file_path = Path(template_file_path)
        self.templates: List[Template] = []
        # カテゴリ名をキー、テンプレートのリストを値とする辞書
        self.templates_by_category: Dict[str, List[Template]] = defaultdict(list)
        
        # テンプレートファイルを読み込む
        self._load_templates()
    
    @with_error_handling(TemplateError, "テンプレートの読み込みに失敗しました")
    def _load_templates(self) -> None:
        """
        テンプレートCSVファイルを読み込み、テンプレートのリストとカテゴリー別辞書を作成します。
        
        Raises:
            TemplateError: CSVファイルが見つからない、ヘッダーが不正、またはデータ形式エラーの場合
        """
        if not self.template_file_path.exists():
            raise TemplateError(
                f"テンプレートファイルが見つかりません: {self.template_file_path}",
                template_file=str(self.template_file_path)
            )
        
        try:
            # テンプレートをクリア
            self.templates.clear()
            self.templates_by_category.clear()
            
            # まずCSVをテキストとして読み込み、行ごとに解析
            with open(self.template_file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)  # ヘッダー行を読み込み
                
                # ヘッダーを検証
                self._validate_headers(headers)
                
                # ヘッダーフィールドのインデックスを取得
                header_indices = {header: i for i, header in enumerate(headers)}
                
                # 各行を処理
                for row in reader:
                    if not row or len(row) < len(self.REQUIRED_FIELDS):
                        continue  # 空行または不足フィールドはスキップ
                    
                    try:
                        # データを取得
                        category = row[header_indices['category']]
                        title = row[header_indices['title']]
                        menu = row[header_indices['menu']]
                        comment = row[header_indices['comment']]
                        hashtag = row[header_indices['hashtag']]
                        
                        # Template オブジェクトを作成
                        template = Template(
                            category=category,
                            title=title,
                            menu=menu,
                            comment=comment,
                            hashtag=hashtag
                        )
                        
                        # テンプレートを追加
                        self.templates.append(template)
                        self.templates_by_category[template.category].append(template)
                        
                    except (IndexError, ValidationError) as e:
                        self.logger.warning(f"無効なテンプレート行をスキップします: {row} - エラー: {e}")
            
            self.logger.info(f"テンプレートの読み込み完了: {len(self.templates)}件のテンプレート、"
                            f"{len(self.templates_by_category)}個のカテゴリ")
            
        except Exception as e:
            raise TemplateError(
                f"テンプレートの読み込みエラー: {str(e)}",
                template_file=str(self.template_file_path)
            ) from e
    
    def _validate_headers(self, headers: List[str]) -> None:
        """
        CSVヘッダーが必要なフィールドを含んでいるかを検証します。
        
        Args:
            headers: CSVのカラム名のリスト
            
        Raises:
            TemplateError: 必須フィールドが不足している場合
        """
        # カラム名の集合を作成
        header_set = set(headers)
        
        # 不足しているフィールドを確認
        missing_fields = self.REQUIRED_FIELDS - header_set
        
        if missing_fields:
            missing_str = ", ".join(missing_fields)
            raise TemplateError(
                f"テンプレートCSVに必須フィールドが不足しています: {missing_str}",
                template_file=str(self.template_file_path),
                details={"missing_fields": list(missing_fields)}
            )
    
    def reload(self) -> None:
        """テンプレートを再読み込みします。"""
        self._load_templates()
    
    def get_templates_by_category(self, category: str) -> List[Template]:
        """
        指定されたカテゴリのテンプレートリストを取得します。
        
        Args:
            category: カテゴリ名
            
        Returns:
            テンプレートリスト（カテゴリが存在しない場合は空リスト）
        """
        return self.templates_by_category.get(category, [])
    
    def get_all_categories(self) -> List[str]:
        """
        全てのカテゴリリストを取得します。
        
        Returns:
            カテゴリリスト
        """
        return list(self.templates_by_category.keys())
    
    def get_all_templates(self) -> List[Template]:
        """
        全てのテンプレートリストを取得します。
        
        Returns:
            テンプレートリスト
        """
        return self.templates.copy()
    
    def find_best_template(self, analysis: StyleAnalysisProtocol) -> Optional[Template]:
        """
        分析結果に最も合うテンプレートを検索します。
        
        Args:
            analysis: 分析結果
            
        Returns:
            最適なテンプレート、または見つからない場合はNone
        """
        # 分析結果のカテゴリに一致するテンプレートを取得
        templates = self.get_templates_by_category(analysis.category)
        
        # テンプレートが見つからない場合
        if not templates:
            self.logger.warning(f"カテゴリ '{analysis.category}' のテンプレートが見つかりません。"
                               f"最も近いカテゴリを検索します。")
            # 最も近いカテゴリを検索
            closest_category = self._find_closest_category(analysis.category)
            if closest_category:
                self.logger.info(f"最も近いカテゴリとして '{closest_category}' を使用します。")
                templates = self.get_templates_by_category(closest_category)
            else:
                self.logger.warning(f"一致するカテゴリが見つかりません。すべてのテンプレートから検索します。")
                templates = self.templates
        
        if not templates:
            return None
        
        # スコアリングとソート
        scored_templates = self._score_templates(templates, analysis)
        if not scored_templates:
            return None
        
        # 最高スコアのテンプレートを返す
        best_template = scored_templates[0][1]
        self.logger.info(f"最適なテンプレートを見つけました: {best_template.title} (スコア: {scored_templates[0][0]:.2f})")
        return best_template
    
    def _find_closest_category(self, category: str) -> Optional[str]:
        """
        指定されたカテゴリ名に最も近いカテゴリを検索します。
        
        Args:
            category: 検索するカテゴリ名
            
        Returns:
            最も近いカテゴリ名、または見つからない場合はNone
        """
        # カテゴリがない場合はNoneを返す
        if not self.templates_by_category:
            return None
        
        # 利用可能なカテゴリのリスト
        available_categories = list(self.templates_by_category.keys())
        
        # difflib.get_close_matches を使用して近いカテゴリを検索
        matches = difflib.get_close_matches(category, available_categories, n=1, cutoff=0.6)
        
        if matches:
            return matches[0]
        
        # マッチするものがない場合は最初のカテゴリを返す
        return available_categories[0]
    
    def _score_templates(self, templates: List[Template], analysis: StyleAnalysisProtocol) -> List[Tuple[float, Template]]:
        """
        テンプレートと分析結果の類似度に基づいてスコアを計算し、スコア順にソートします。
        
        Args:
            templates: スコアリングするテンプレートのリスト
            analysis: 分析結果
            
        Returns:
            (スコア, テンプレート) のタプルのリスト（スコア降順）
        """
        scored_templates = []
        
        # 分析結果からキーワードを取得
        analysis_keywords = set(analysis.keywords) if hasattr(analysis, 'keywords') else set()
        analysis_features = analysis.features
        
        for template in templates:
            score = 0.0
            
            # カテゴリの一致（最も重要）
            if template.category == analysis.category:
                score += 3.0
            
            # キーワードの一致（2番目に重要）
            template_tags = set(template.get_hashtags())
            if template_tags and analysis_keywords:
                # 共通するキーワードの割合
                common_keywords = template_tags.intersection(analysis_keywords)
                keyword_score = len(common_keywords) / max(len(template_tags), 1) * 2.0
                score += keyword_score
            
            # テキスト内容の類似度（3番目に重要）
            # タイトル、コメント、メニューなどのテキスト内容に分析結果の特徴が含まれているかを評価
            combined_text = f"{template.title} {template.comment} {template.menu}".lower()
            
            # Pydanticモデルは辞書のようにアクセスできないため、属性として取得
            feature_values = {
                'color': analysis_features.color,
                'cut_technique': analysis_features.cut_technique,
                'styling': analysis_features.styling,
                'impression': analysis_features.impression
            }
            
            for feature_key, feature_value in feature_values.items():
                if feature_value.lower() in combined_text:
                    score += 0.5
            
            scored_templates.append((score, template))
        
        # スコア降順でソート
        return sorted(scored_templates, key=lambda x: x[0], reverse=True)
