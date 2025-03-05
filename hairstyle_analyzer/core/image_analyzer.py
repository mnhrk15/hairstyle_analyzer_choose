"""
画像分析モジュール

このモジュールでは、Google Gemini APIを使用して画像分析を行う機能を提供します。
画像のカテゴリ判定、特徴抽出、属性分析（性別・髪の長さ）などの機能が含まれます。
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Union, Tuple

from ..data.models import StyleAnalysis, AttributeAnalysis
from ..data.interfaces import StyleAnalysisProtocol, AttributeAnalysisProtocol, CacheManagerProtocol
from ..services.gemini import GeminiService
from ..utils.errors import GeminiAPIError, ImageError, async_with_error_handling


class ImageAnalyzer:
    """
    画像分析クラス
    
    Google Gemini APIを使用して、画像の分析を行います。
    カテゴリ判定、特徴抽出、属性分析（性別・髪の長さ）などの機能が含まれます。
    """
    
    def __init__(self, gemini_service: GeminiService, cache_manager: Optional[CacheManagerProtocol] = None):
        """
        初期化
        
        Args:
            gemini_service: Gemini APIサービス
            cache_manager: キャッシュマネージャー（オプション）
        """
        self.logger = logging.getLogger(__name__)
        self.gemini_service = gemini_service
        self.cache_manager = cache_manager
    
    async def analyze_image(self, image_path: Path, categories: List[str]) -> Optional[StyleAnalysisProtocol]:
        """
        画像を分析します。
        
        Args:
            image_path: 画像ファイルのパス
            categories: カテゴリリスト
            
        Returns:
            分析結果、またはエラー時はNone
            
        Raises:
            ImageError: 画像が無効な場合
            GeminiAPIError: API呼び出しに失敗した場合
        """
        self.logger.info(f"画像分析開始: {image_path.name}")
        
        # キャッシュチェック
        if self.cache_manager:
            cache_key = f"style_analysis:{image_path.name}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.info(f"キャッシュから分析結果を取得: {image_path.name}")
                return cached_result
        
        # Gemini APIで画像を分析
        try:
            analysis = await self.gemini_service.analyze_image(image_path, categories)
            
            # 結果をキャッシュに保存
            if analysis and self.cache_manager:
                self.cache_manager.set(cache_key, analysis)
                
            return analysis
            
        except (GeminiAPIError, ImageError) as e:
            self.logger.error(f"画像分析エラー: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            return None
    
    async def analyze_attributes(self, image_path: Path) -> Optional[AttributeAnalysisProtocol]:
        """
        画像の属性（性別・髪の長さ）を分析します。
        
        Args:
            image_path: 画像ファイルのパス
            
        Returns:
            属性分析結果、またはエラー時はNone
            
        Raises:
            ImageError: 画像が無効な場合
            GeminiAPIError: API呼び出しに失敗した場合
        """
        self.logger.info(f"属性分析開始: {image_path.name}")
        
        # キャッシュチェック
        if self.cache_manager:
            cache_key = f"attribute_analysis:{image_path.name}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.info(f"キャッシュから属性分析結果を取得: {image_path.name}")
                return cached_result
        
        # Gemini APIで属性を分析
        try:
            attributes = await self.gemini_service.analyze_attributes(image_path)
            
            # 結果をキャッシュに保存
            if attributes and self.cache_manager:
                self.cache_manager.set(cache_key, attributes)
                
            return attributes
            
        except (GeminiAPIError, ImageError) as e:
            self.logger.error(f"属性分析エラー: {str(e)}")
            raise
            
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            return None
    
    async def analyze_full(self, image_path: Path, categories: List[str]) -> Tuple[Optional[StyleAnalysisProtocol], Optional[AttributeAnalysisProtocol]]:
        """
        画像の完全分析（スタイル分析と属性分析）を行います。
        
        Args:
            image_path: 画像ファイルのパス
            categories: カテゴリリスト
            
        Returns:
            (スタイル分析結果, 属性分析結果)のタプル
        """
        self.logger.info(f"完全分析開始: {image_path.name}")
        
        # 並列で両方の分析を実行
        style_task = self.analyze_image(image_path, categories)
        attribute_task = self.analyze_attributes(image_path)
        
        # 両方の結果を待機
        results = await asyncio.gather(style_task, attribute_task, return_exceptions=True)
        
        # 結果の処理
        style_result = None
        attribute_result = None
        
        if not isinstance(results[0], Exception):
            style_result = results[0]
            # 辞書型の場合はStyleAnalysisに変換
            if isinstance(style_result, dict):
                try:
                    from ..data.models import StyleAnalysis, StyleFeatures
                    features = StyleFeatures(**style_result.get('features', {}))
                    style_result = StyleAnalysis(
                        category=style_result.get('category', ''),
                        features=features,
                        keywords=style_result.get('keywords', [])
                    )
                except Exception as e:
                    self.logger.error(f"スタイル分析結果の変換に失敗しました: {e}")
                    style_result = None
        else:
            self.logger.error(f"スタイル分析エラー: {str(results[0])}")
        
        if not isinstance(results[1], Exception):
            attribute_result = results[1]
            # 辞書型の場合はAttributeAnalysisに変換
            if isinstance(attribute_result, dict):
                try:
                    from ..data.models import AttributeAnalysis
                    attribute_result = AttributeAnalysis(
                        sex=attribute_result.get('sex', ''),
                        length=attribute_result.get('length', '')
                    )
                except Exception as e:
                    self.logger.error(f"属性分析結果の変換に失敗しました: {e}")
                    attribute_result = None
        else:
            self.logger.error(f"属性分析エラー: {str(results[1])}")
        
        return style_result, attribute_result
