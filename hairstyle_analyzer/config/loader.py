"""
設定ファイルの読み込みを行うモジュール

このモジュールでは、YAMLファイルからアプリケーション設定を読み込み、
Pydanticモデルに変換する機能を提供します。
"""

import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union

import yaml
from yaml.loader import SafeLoader

from hairstyle_analyzer.config.models import (
    AppConfig, ScraperConfig, GeminiConfig, 
    CacheConfig, ExcelConfig, ProcessingConfig,
    PathConfig, LoggingConfig
)


class ConfigLoader:
    """
    設定ファイルを読み込むクラス
    
    YAMLファイルから設定を読み込み、Pydanticモデルに変換します。
    """
    
    def __init__(self, config_path: Union[str, Path]):
        """
        ConfigLoaderの初期化
        
        Args:
            config_path: 設定ファイルのパス
        """
        self.logger = logging.getLogger(__name__)
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        
    def load(self) -> AppConfig:
        """
        設定ファイルを読み込みます
        
        Returns:
            アプリケーション設定
            
        Raises:
            FileNotFoundError: 設定ファイルが見つからない場合
            yaml.YAMLError: YAMLの解析エラーが発生した場合
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"設定ファイルが見つかりません: {self.config_path}")
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.load(f, Loader=SafeLoader)
                
            self.logger.info(f"設定ファイルを読み込みました: {self.config_path}")
            return AppConfig(**self._config)
        except yaml.YAMLError as e:
            self.logger.error(f"設定ファイルの解析エラー: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"設定ファイルの読み込みエラー: {str(e)}")
            raise
            
    def get_scraper_config(self) -> ScraperConfig:
        """
        スクレイパー設定を取得します
        
        Returns:
            スクレイパー設定
        """
        if not self._config:
            self.load()
        return ScraperConfig(**self._config['scraper'])
        
    def get_gemini_config(self) -> GeminiConfig:
        """
        Gemini API設定を取得します
        
        Returns:
            Gemini API設定
        """
        if not self._config:
            self.load()
        return GeminiConfig(**self._config['gemini'])
        
    def get_cache_config(self) -> CacheConfig:
        """
        キャッシュ設定を取得します
        
        Returns:
            キャッシュ設定
        """
        if not self._config:
            self.load()
        return CacheConfig(**self._config['cache'])
        
    def get_excel_config(self) -> ExcelConfig:
        """
        Excel出力設定を取得します
        
        Returns:
            Excel出力設定
        """
        if not self._config:
            self.load()
        return ExcelConfig(**self._config['excel'])
        
    def get_processing_config(self) -> ProcessingConfig:
        """
        処理設定を取得します
        
        Returns:
            処理設定
        """
        if not self._config:
            self.load()
        return ProcessingConfig(**self._config['processing'])
        
    def get_path_config(self) -> PathConfig:
        """
        パス設定を取得します
        
        Returns:
            パス設定
        """
        if not self._config:
            self.load()
        return PathConfig(**self._config['paths'])
        
    def get_logging_config(self) -> LoggingConfig:
        """
        ロギング設定を取得します
        
        Returns:
            ロギング設定
        """
        if not self._config:
            self.load()
        return LoggingConfig(**self._config['logging'])
