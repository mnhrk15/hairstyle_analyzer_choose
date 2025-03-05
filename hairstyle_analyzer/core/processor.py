"""
処理フローモジュール

このモジュールでは、アプリケーションの中心となる処理フローを定義します。
画像処理、テンプレートマッチング、スタイリスト・クーポン選択、Excel出力などの処理を制御します。
"""

import os
import asyncio
import logging
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set, Union
from datetime import datetime

import tqdm.asyncio
from tqdm import tqdm

from ..data.models import ProcessResult, StyleAnalysis, AttributeAnalysis
from ..data.interfaces import (
    ProcessResultProtocol, MainProcessorProtocol, CacheManagerProtocol,
    StyleAnalysisProtocol, AttributeAnalysisProtocol, StylistInfoProtocol, CouponInfoProtocol
)
from ..utils.errors import (
    AppError, ProcessingError, ImageError, GeminiAPIError, 
    ScraperError, TemplateError, ValidationError
)
from ..utils.system_utils import calculate_optimal_batch_size
from .image_analyzer import ImageAnalyzer
from .template_matcher import TemplateMatcher
from .style_matching import StyleMatchingService
from .excel_exporter import ExcelExporter


class MainProcessor(MainProcessorProtocol):
    """
    メイン処理フロークラス
    
    アプリケーションの中心となる処理フローを制御します。
    画像処理、テンプレートマッチング、スタイリスト・クーポン選択、Excel出力などの処理を統合します。
    """
    
    def __init__(
        self, 
        image_analyzer: ImageAnalyzer,
        template_matcher: TemplateMatcher,
        style_matcher: StyleMatchingService,
        excel_exporter: ExcelExporter,
        cache_manager: Optional[CacheManagerProtocol] = None,
        batch_size: int = 5,
        api_delay: float = 1.0,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ):
        """
        初期化
        
        Args:
            image_analyzer: 画像分析クラス
            template_matcher: テンプレートマッチングクラス
            style_matcher: スタイルマッチングサービス
            excel_exporter: Excel出力クラス
            cache_manager: キャッシュマネージャー（オプション）
            batch_size: バッチサイズ
            api_delay: API呼び出し間の遅延（秒）
            max_retries: 最大リトライ回数
            retry_delay: リトライ間隔（秒）
        """
        self.logger = logging.getLogger(__name__)
        self.image_analyzer = image_analyzer
        self.template_matcher = template_matcher
        self.style_matcher = style_matcher
        self.excel_exporter = excel_exporter
        self.cache_manager = cache_manager
        
        # 設定パラメータ
        self.batch_size = batch_size
        self.api_delay = api_delay
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        
        # 処理結果
        self.results: List[ProcessResult] = []
        
        # 進捗表示用
        self.progress_callback = None
    
    def set_progress_callback(self, callback) -> None:
        """
        進捗コールバックを設定します。
        
        Args:
            callback: 進捗状況を通知するコールバック関数
        """
        self.progress_callback = callback
    
    def _update_progress(self, current: int, total: int, message: str = "") -> None:
        """
        進捗状況を更新します。
        
        Args:
            current: 現在の進捗
            total: 全体の作業量
            message: 進捗メッセージ
        """
        if self.progress_callback:
            self.progress_callback(current, total, message)
    
    async def process_single_image(self, image_path: Path, stylists=None, coupons=None) -> Optional[ProcessResultProtocol]:
        """
        単一の画像を処理します。
        
        Args:
            image_path: 画像ファイルのパス
            stylists: スタイリスト情報のリスト（オプション）
            coupons: クーポン情報のリスト（オプション）
            
        Returns:
            処理結果、またはエラー時はNone
            
        Raises:
            ProcessingError: 処理中にエラーが発生した場合
            ImageError: 画像が無効な場合
        """
        self.logger.info(f"画像処理開始: {image_path.name}")
        
        # キャッシュチェック
        if self.cache_manager:
            cache_key = f"process_result:{image_path.name}"
            cached_result = self.cache_manager.get(cache_key)
            if cached_result:
                self.logger.info(f"キャッシュから処理結果を取得: {image_path.name}")
                return cached_result
        
        try:
            # 1. スタイル分析と属性分析を並列実行
            categories = self.template_matcher.template_manager.get_all_categories()
            style_analysis, attribute_analysis = await self.image_analyzer.analyze_full(image_path, categories)
            
            if not style_analysis or not attribute_analysis:
                self.logger.error(f"画像分析に失敗しました: {image_path.name}")
                return None
            
            # 2. テンプレートマッチング
            template = self.template_matcher.find_best_template(style_analysis)
            
            if not template:
                self.logger.error(f"テンプレートマッチングに失敗しました: {image_path.name}")
                return None
            
            # 3-4. スタイリストとクーポン選択
            selected_stylist = None
            selected_coupon = None
            stylist_reason = None
            coupon_reason = None
            
            # スタイリスト選択
            if stylists and len(stylists) > 0:
                selected_stylist, stylist_reason = await self.style_matcher.select_stylist(
                    image_path, stylists, style_analysis
                )
                self.logger.info(f"スタイリスト選択: {selected_stylist.name if selected_stylist else 'なし'}")
            else:
                # ダミースタイリスト
                from ..data.models import StylistInfo
                selected_stylist = StylistInfo(
                    name="サンプルスタイリスト",
                    description="サンプル説明",
                    position="スタイリスト"
                )
            
            # クーポン選択
            if coupons and len(coupons) > 0:
                selected_coupon, coupon_reason = await self.style_matcher.select_coupon(
                    image_path, coupons, style_analysis
                )
                self.logger.info(f"クーポン選択: {selected_coupon.name if selected_coupon else 'なし'}")
            else:
                # ダミークーポン
                from ..data.models import CouponInfo
                selected_coupon = CouponInfo(
                    name="サンプルクーポン",
                    price="1000円"
                )
            
            # 5. 処理結果の作成
            try:
                # スタイル分析が辞書型の場合はStyleAnalysisに変換
                if isinstance(style_analysis, dict):
                    from ..data.models import StyleAnalysis, StyleFeatures
                    features = StyleFeatures(**style_analysis.get('features', {}))
                    style_analysis = StyleAnalysis(
                        category=style_analysis.get('category', ''),
                        features=features,
                        keywords=style_analysis.get('keywords', [])
                    )
                
                # 属性分析が辞書型の場合はAttributeAnalysisに変換
                if isinstance(attribute_analysis, dict):
                    from ..data.models import AttributeAnalysis
                    attribute_analysis = AttributeAnalysis(
                        sex=attribute_analysis.get('sex', ''),
                        length=attribute_analysis.get('length', '')
                    )
                
                # スタイリストが辞書型の場合はStylistInfoに変換
                if isinstance(selected_stylist, dict):
                    from ..data.models import StylistInfo
                    selected_stylist = StylistInfo(
                        name=selected_stylist.get('name', 'サンプルスタイリスト'),
                        specialties=selected_stylist.get('specialties', ''),
                        description=selected_stylist.get('description', '')
                    )
                
                # クーポンが辞書型の場合はCouponInfoに変換
                if isinstance(selected_coupon, dict):
                    from ..data.models import CouponInfo
                    selected_coupon = CouponInfo(
                        name=selected_coupon.get('name', 'サンプルクーポン'),
                        price=selected_coupon.get('price', 0),
                        description=selected_coupon.get('description', ''),
                        categories=selected_coupon.get('categories', []),
                        conditions=selected_coupon.get('conditions', {})
                    )
                
                # テンプレートが辞書型の場合はTemplateに変換
                if isinstance(template, dict):
                    from ..data.models import Template
                    template = Template(
                        category=template.get('category', ''),
                        title=template.get('title', ''),
                        menu=template.get('menu', ''),
                        comment=template.get('comment', ''),
                        hashtag=template.get('hashtag', '')
                    )
                
                result = ProcessResult(
                    image_name=image_path.name,
                    style_analysis=style_analysis,
                    attribute_analysis=attribute_analysis,
                    selected_template=template,
                    selected_stylist=selected_stylist,
                    selected_coupon=selected_coupon,
                    processed_at=datetime.now(),
                    stylist_reason=stylist_reason,
                    coupon_reason=coupon_reason
                )
            except Exception as e:
                self.logger.error(f"処理結果の作成に失敗しました: {str(e)}")
                raise ProcessingError(f"処理結果の作成に失敗しました: {str(e)}")
            
            # 結果をキャッシュに保存
            if self.cache_manager:
                self.cache_manager.set(cache_key, result)
            
            self.logger.info(f"画像処理完了: {image_path.name}")
            return result
            
        except (ImageError, GeminiAPIError, TemplateError) as e:
            self.logger.error(f"画像処理エラー: {str(e)}")
            raise ProcessingError(f"画像処理中にエラーが発生しました: {str(e)}", 
                                image_path=str(image_path)) from e
        
        except Exception as e:
            self.logger.error(f"予期しないエラー: {str(e)}")
            raise ProcessingError(f"画像処理中に予期しないエラーが発生しました: {str(e)}", 
                                image_path=str(image_path)) from e
    
    async def process_images(self, image_paths: List[Path]) -> List[ProcessResultProtocol]:
        """
        複数の画像を処理します。
        
        Args:
            image_paths: 画像ファイルのパスリスト
            
        Returns:
            処理結果のリスト
        """
        self.logger.info(f"複数画像処理開始: {len(image_paths)}枚")
        
        # 結果リストをクリア
        self.results = []
        
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return []
        
        # 最適なバッチサイズを計算
        optimal_batch_size = calculate_optimal_batch_size(
            memory_per_item_mb=5,  # 1画像あたりの推定メモリ使用量
            max_batch_size=self.batch_size
        )
        
        self.logger.info(f"バッチサイズを設定: {optimal_batch_size}")
        
        # 画像をバッチに分割
        total_images = len(image_paths)
        batch_count = (total_images + optimal_batch_size - 1) // optimal_batch_size
        batches = [image_paths[i:i + optimal_batch_size] for i in range(0, total_images, optimal_batch_size)]
        
        # 進捗更新
        self._update_progress(0, total_images, "処理準備完了")
        
        processed_count = 0
        
        # バッチごとに処理
        for batch_index, batch in enumerate(batches):
            batch_message = f"バッチ {batch_index + 1}/{batch_count} 処理中"
            self.logger.info(batch_message)
            self._update_progress(processed_count, total_images, batch_message)
            
            # バッチ内の画像を並列処理
            tasks = [self.process_single_image(image_path) for image_path in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果の処理
            for i, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    # エラーをログに記録
                    self.logger.error(f"画像処理中にエラーが発生しました: {str(result)}")
                    # エラーが発生した画像のパスを取得
                    error_image = batch[i].name if i < len(batch) else "不明"
                    self._update_progress(processed_count + i + 1, total_images, f"エラー: {error_image}")
                elif result:
                    # 正常な結果を追加
                    self.results.append(result)
                
                processed_count += 1
                self._update_progress(processed_count, total_images)
            
            # APIレート制限に対応するための遅延
            if batch_index < len(batches) - 1:
                await asyncio.sleep(self.api_delay)
        
        # 最終進捗更新
        self._update_progress(total_images, total_images, f"処理完了: {len(self.results)}/{total_images}枚")
        
        self.logger.info(f"複数画像処理完了: {len(self.results)}/{total_images}枚")
        return self.results
    
    async def process_images_with_external_data(
        self, 
        image_paths: List[Path],
        stylists: List[StylistInfoProtocol],
        coupons: List[CouponInfoProtocol]
    ) -> List[ProcessResultProtocol]:
        """
        外部データ（スタイリスト・クーポン情報）を使用して複数の画像を処理します。
        
        Args:
            image_paths: 画像ファイルのパスリスト
            stylists: スタイリスト情報のリスト
            coupons: クーポン情報のリスト
            
        Returns:
            処理結果のリスト
        """
        self.logger.info(f"外部データを使用した複数画像処理開始: {len(image_paths)}枚")
        
        # 結果リストをクリア
        self.results = []
        
        if not image_paths:
            self.logger.warning("処理する画像がありません")
            return []
        
        if not stylists:
            self.logger.warning("スタイリスト情報がありません")
            return []
        
        if not coupons:
            self.logger.warning("クーポン情報がありません")
            return []
        
        # 最適なバッチサイズを計算
        optimal_batch_size = calculate_optimal_batch_size(
            memory_per_item_mb=5,  # 1画像あたりの推定メモリ使用量
            max_batch_size=self.batch_size
        )
        
        self.logger.info(f"バッチサイズを設定: {optimal_batch_size}")
        
        # 画像をバッチに分割
        total_images = len(image_paths)
        batch_count = (total_images + optimal_batch_size - 1) // optimal_batch_size
        batches = [image_paths[i:i + optimal_batch_size] for i in range(0, total_images, optimal_batch_size)]
        
        # 進捗更新
        self._update_progress(0, total_images, "処理準備完了")
        
        processed_count = 0
        
        # バッチごとに処理
        for batch_index, batch in enumerate(batches):
            batch_message = f"バッチ {batch_index + 1}/{batch_count} 処理中"
            self.logger.info(batch_message)
            self._update_progress(processed_count, total_images, batch_message)
            
            # バッチ内の各画像を順次処理
            for image_path in batch:
                try:
                    # キャッシュチェック
                    if self.cache_manager:
                        cache_key = f"process_result_ext:{image_path.name}"
                        cached_result = self.cache_manager.get(cache_key)
                        if cached_result:
                            self.logger.info(f"キャッシュから処理結果を取得: {image_path.name}")
                            self.results.append(cached_result)
                            processed_count += 1
                            self._update_progress(processed_count, total_images, f"キャッシュ: {image_path.name}")
                            continue
                    
                    # 1. スタイル分析と属性分析を並列実行
                    categories = self.template_matcher.template_manager.get_all_categories()
                    style_analysis, attribute_analysis = await self.image_analyzer.analyze_full(image_path, categories)
                    
                    if not style_analysis or not attribute_analysis:
                        self.logger.error(f"画像分析に失敗しました: {image_path.name}")
                        processed_count += 1
                        self._update_progress(processed_count, total_images, f"分析失敗: {image_path.name}")
                        continue
                    
                    # 2. テンプレートマッチング
                    template = self.template_matcher.find_best_template(style_analysis)
                    
                    if not template:
                        self.logger.error(f"テンプレートマッチングに失敗しました: {image_path.name}")
                        processed_count += 1
                        self._update_progress(processed_count, total_images, f"マッチング失敗: {image_path.name}")
                        continue
                    
                    # 3. スタイリスト選択
                    selected_stylist = await self.style_matcher.select_stylist(
                        image_path, stylists, style_analysis
                    )
                    
                    # 4. クーポン選択
                    selected_coupon = await self.style_matcher.select_coupon(
                        image_path, coupons, style_analysis
                    )
                    
                    # 5. 処理結果の作成
                    try:
                        # スタイル分析が辞書型の場合はStyleAnalysisに変換
                        if isinstance(style_analysis, dict):
                            from ..data.models import StyleAnalysis, StyleFeatures
                            features = StyleFeatures(**style_analysis.get('features', {}))
                            style_analysis = StyleAnalysis(
                                category=style_analysis.get('category', ''),
                                features=features,
                                keywords=style_analysis.get('keywords', [])
                            )
                        
                        # 属性分析が辞書型の場合はAttributeAnalysisに変換
                        if isinstance(attribute_analysis, dict):
                            from ..data.models import AttributeAnalysis
                            attribute_analysis = AttributeAnalysis(
                                sex=attribute_analysis.get('sex', ''),
                                length=attribute_analysis.get('length', '')
                            )
                        
                        # スタイリストが辞書型の場合はStylistInfoに変換
                        if isinstance(selected_stylist, dict):
                            from ..data.models import StylistInfo
                            selected_stylist = StylistInfo(
                                name=selected_stylist.get('name', 'サンプルスタイリスト'),
                                specialties=selected_stylist.get('specialties', ''),
                                description=selected_stylist.get('description', '')
                            )
                        
                        # クーポンが辞書型の場合はCouponInfoに変換
                        if isinstance(selected_coupon, dict):
                            from ..data.models import CouponInfo
                            selected_coupon = CouponInfo(
                                name=selected_coupon.get('name', 'サンプルクーポン'),
                                price=selected_coupon.get('price', 0),
                                description=selected_coupon.get('description', ''),
                                categories=selected_coupon.get('categories', []),
                                conditions=selected_coupon.get('conditions', {})
                            )
                        
                        # テンプレートが辞書型の場合はTemplateに変換
                        if isinstance(template, dict):
                            from ..data.models import Template
                            template = Template(
                                category=template.get('category', ''),
                                title=template.get('title', ''),
                                menu=template.get('menu', ''),
                                comment=template.get('comment', ''),
                                hashtag=template.get('hashtag', '')
                            )
                        
                        result = ProcessResult(
                            image_name=image_path.name,
                            style_analysis=style_analysis,
                            attribute_analysis=attribute_analysis,
                            selected_template=template,
                            selected_stylist=selected_stylist,
                            selected_coupon=selected_coupon,
                            processed_at=datetime.now()
                        )
                    except Exception as e:
                        self.logger.error(f"処理結果の作成に失敗しました: {str(e)}")
                    
                    # 結果をキャッシュに保存
                    if self.cache_manager:
                        self.cache_manager.set(cache_key, result)
                    
                    # 結果を追加
                    self.results.append(result)
                    self.logger.info(f"画像処理完了: {image_path.name}")
                    
                except Exception as e:
                    self.logger.error(f"画像 {image_path.name} の処理中にエラーが発生しました: {str(e)}")
                
                # 進捗更新
                processed_count += 1
                self._update_progress(processed_count, total_images, f"処理: {image_path.name}")
                
                # APIレート制限に対応するための遅延
                await asyncio.sleep(self.api_delay)
            
            # バッチ間の遅延
            if batch_index < len(batches) - 1:
                await asyncio.sleep(self.api_delay * 2)
        
        # 最終進捗更新
        self._update_progress(total_images, total_images, f"処理完了: {len(self.results)}/{total_images}枚")
        
        self.logger.info(f"外部データを使用した複数画像処理完了: {len(self.results)}/{total_images}枚")
        return self.results
    
    def export_to_excel(self, output_path: Path) -> Path:
        """
        処理結果をExcelファイルに出力します。
        
        Args:
            output_path: 出力ファイルのパス
            
        Returns:
            エクスポートされたファイルのパス
            
        Raises:
            ExcelExportError: Excel出力処理でエラーが発生した場合
        """
        self.logger.info(f"Excel出力開始: 結果数={len(self.results)}, 出力先={output_path}")
        
        if not self.results:
            self.logger.warning("出力する結果がありません")
            raise ValidationError("出力する結果がありません")
        
        # Excel出力
        return self.excel_exporter.export(self.results, output_path)
    
    def get_excel_binary(self) -> bytes:
        """
        処理結果のExcelバイナリデータを取得します。
        
        Returns:
            Excelバイナリデータ
            
        Raises:
            ExcelExportError: Excel出力処理でエラーが発生した場合
        """
        self.logger.info(f"Excelバイナリデータ生成開始: 結果数={len(self.results)}")
        
        if not self.results:
            self.logger.warning("出力する結果がありません")
            raise ValidationError("出力する結果がありません")
        
        # Excelバイナリデータの取得
        return self.excel_exporter.get_binary_data(self.results)
    
    def get_results(self) -> List[ProcessResultProtocol]:
        """
        処理結果のリストを取得します。
        
        Returns:
            処理結果のリスト
        """
        return self.results
    
    def clear_results(self) -> None:
        """
        処理結果をクリアします。
        """
        self.results = []
        self.logger.info("処理結果をクリアしました")
    
    async def retry_failed_images(self, image_paths: List[Path]) -> List[ProcessResultProtocol]:
        """
        失敗した画像を再処理します。
        
        Args:
            image_paths: 再処理する画像のパスリスト
            
        Returns:
            処理結果のリスト
        """
        self.logger.info(f"失敗画像の再処理開始: {len(image_paths)}枚")
        
        # 現在のキャッシュ設定を保存
        cache_enabled = self.cache_manager is not None
        
        # 再処理用にキャッシュを無効化
        self.cache_manager = None
        
        # 画像を再処理
        results = await self.process_images(image_paths)
        
        # 元のキャッシュ設定を復元
        if cache_enabled:
            # ここでキャッシュマネージャーを再設定する必要があります
            # 実際の実装では適切なキャッシュマネージャーを設定してください
            pass
        
        return results
