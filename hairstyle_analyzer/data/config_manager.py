"""
設定マネージャーモジュール

このモジュールでは、アプリケーションの設定を管理するためのConfigManagerクラスを定義します。
設定ファイル（YAML）の読み込み、環境変数の管理、設定値の検証と利用を提供します。
"""

import os
import yaml
import logging
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from datetime import datetime
from dotenv import load_dotenv

from .models import (
    AppConfig, GeminiConfig, ScraperConfig, ExcelConfig,
    ProcessingConfig, PathsConfig, CacheConfig, LoggingConfig, TextConfig
)


class ConfigManager:
    """設定マネージャークラス
    
    YAMLファイルからアプリケーション設定を読み込み、環境変数と組み合わせて
    アプリケーション設定を提供します。
    """
    
    DEFAULT_CONFIG_PATH = Path("config/config.yaml")
    ENV_FILE = Path(".env")
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        """
        ConfigManagerの初期化
        
        Args:
            config_path: 設定ファイルのパス（オプション）
        """
        # 環境変数のロード
        load_dotenv(self.ENV_FILE)
        
        # 設定ファイルパスの設定
        self.config_path = Path(config_path) if config_path else self.DEFAULT_CONFIG_PATH
        self.backup_path = self.config_path.with_suffix('.yaml.bak')
        
        # 設定の読み込みと初期化
        self._config_dict = self._load_config()
        
        # Pydanticモデルへの変換
        self._app_config = self._create_app_config()
        
        # ロギングの設定
        self._setup_logging()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        設定ファイルをロードする内部メソッド
        
        Returns:
            設定辞書
        """
        try:
            if not self.config_path.exists():
                print(f"設定ファイルが見つかりません: {self.config_path}")
                return {}
            
            with open(self.config_path, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
                return config if config is not None else {}
        except Exception as e:
            print(f"設定ファイルの読み込みエラー: {e}")
            return {}
    
    def _create_app_config(self) -> AppConfig:
        """
        設定辞書からAppConfigモデルを作成
        
        Returns:
            AppConfigインスタンス
        """
        try:
            # 環境変数からAPIキーを取得
            gemini_api_key = os.getenv("GEMINI_API_KEY", "")
            
            # 設定辞書から各設定セクションを取得
            gemini_dict = self._config_dict.get('gemini', {})
            scraper_dict = self._config_dict.get('scraper', {})
            excel_dict = self._config_dict.get('excel', {})
            text_dict = self._config_dict.get('text', {})
            processing_dict = self._config_dict.get('processing', {})
            paths_dict = self._config_dict.get('paths', {})
            cache_dict = self._config_dict.get('cache', {})
            logging_dict = self._config_dict.get('logging', {})
            
            # APIキーを設定辞書に追加
            gemini_dict['api_key'] = gemini_api_key
            
            # パス設定を文字列からPathオブジェクトに変換
            for key, value in paths_dict.items():
                if isinstance(value, str):
                    paths_dict[key] = Path(value)
            
            # ログファイルパスをPathオブジェクトに変換
            if 'log_file' in logging_dict and isinstance(logging_dict['log_file'], str):
                logging_dict['log_file'] = Path(logging_dict['log_file'])
            
            # AppConfigモデルを作成
            return AppConfig(
                gemini=GeminiConfig(**gemini_dict),
                scraper=ScraperConfig(**scraper_dict),
                excel=ExcelConfig(**excel_dict),
                text=TextConfig(**text_dict),
                processing=ProcessingConfig(**processing_dict),
                paths=PathsConfig(**paths_dict),
                cache=CacheConfig(**cache_dict),
                logging=LoggingConfig(**logging_dict)
            )
        except Exception as e:
            print(f"設定モデルの作成エラー: {e}")
            raise
    
    def _setup_logging(self) -> None:
        """ロギングを設定する内部メソッド"""
        try:
            log_config = self._app_config.logging
            log_dir = log_config.log_file.parent
            
            # ログディレクトリの作成
            log_dir.mkdir(parents=True, exist_ok=True)
            
            # ロギングの設定
            logging.basicConfig(
                level=getattr(logging, log_config.log_level),
                format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                handlers=[
                    logging.FileHandler(log_config.log_file, encoding='utf-8'),
                    logging.StreamHandler()
                ]
            )
            
            logging.info("ロギングを初期化しました")
        except Exception as e:
            print(f"ロギング設定エラー: {e}")
    
    def _create_backup(self) -> None:
        """設定ファイルのバックアップを作成"""
        try:
            if self.config_path.exists():
                shutil.copy2(self.config_path, self.backup_path)
                logging.info(f"設定ファイルのバックアップを作成: {self.backup_path}")
        except Exception as e:
            logging.error(f"バックアップ作成失敗: {e}")
            raise
    
    def _restore_backup(self) -> None:
        """バックアップから設定ファイルを復元"""
        try:
            if self.backup_path.exists():
                shutil.copy2(self.backup_path, self.config_path)
                logging.info("バックアップから復元完了")
                
                # 設定を再読み込み
                self._config_dict = self._load_config()
                self._app_config = self._create_app_config()
        except Exception as e:
            logging.error(f"バックアップ復元失敗: {e}")
            raise
    
    def save_config(self) -> None:
        """現在の設定をYAMLファイルに保存"""
        try:
            # バックアップの作成
            self._create_backup()
            
            # 設定の保存
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self._config_dict, f, sort_keys=False, allow_unicode=True)
            
            logging.info(f"設定を保存しました: {self.config_path}")
        except Exception as e:
            logging.error(f"設定の保存に失敗: {e}")
            self._restore_backup()
            raise
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """
        設定辞書を更新し、保存する
        
        Args:
            new_config: 新しい設定辞書
        """
        try:
            # バックアップの作成
            self._create_backup()
            
            # 設定の更新
            self._config_dict.update(new_config)
            
            # 設定の保存
            self.save_config()
            
            # モデルの再作成
            self._app_config = self._create_app_config()
            
            logging.info("設定を更新しました")
        except Exception as e:
            logging.error(f"設定の更新に失敗: {e}")
            self._restore_backup()
            raise
    
    def validate(self) -> None:
        """設定値を検証する"""
        try:
            # 必要なディレクトリの確認と作成
            for path_name in ['image_folder', 'template_csv', 'output_excel', 'cache_file', 'log_file']:
                path = getattr(self._app_config.paths, path_name)
                dir_path = path.parent
                dir_path.mkdir(parents=True, exist_ok=True)
                logging.info(f"ディレクトリを確認/作成: {dir_path}")
            
            # APIキーの確認
            if not self._app_config.gemini.api_key:
                logging.warning("Gemini APIキーが設定されていません")
            
            # スクレイパーURLの確認
            if not self._app_config.scraper.base_url:
                logging.warning("スクレイパーのベースURLが設定されていません")
            
            logging.info("設定の検証が完了しました")
        except Exception as e:
            logging.error(f"設定の検証に失敗: {e}")
            raise
    
    def save_api_key(self, api_key: str) -> None:
        """
        Gemini APIキーを.envファイルに保存
        
        Args:
            api_key: APIキー
        """
        try:
            env_content = []
            
            # 既存の.envファイルを読み込む
            if self.ENV_FILE.exists():
                with open(self.ENV_FILE, 'r', encoding='utf-8') as f:
                    env_content = [
                        line for line in f.readlines()
                        if not line.startswith('GEMINI_API_KEY=')
                    ]
            
            # APIキーを追加
            env_content.append(f'GEMINI_API_KEY={api_key}\n')
            
            # .envファイルに書き込む
            with open(self.ENV_FILE, 'w', encoding='utf-8') as f:
                f.writelines(env_content)
            
            # 環境変数を更新
            os.environ['GEMINI_API_KEY'] = api_key
            
            # 設定モデルを更新
            gemini_dict = self._config_dict.get('gemini', {})
            gemini_dict['api_key'] = api_key
            self._app_config = self._create_app_config()
            
            logging.info("APIキーを保存しました")
        except Exception as e:
            logging.error(f"APIキーの保存に失敗: {e}")
            raise
    
    @property
    def app_config(self) -> AppConfig:
        """アプリケーション設定モデルを取得"""
        return self._app_config
    
    @property
    def gemini(self) -> GeminiConfig:
        """Gemini API設定モデルを取得"""
        return self._app_config.gemini
    
    @property
    def scraper(self) -> ScraperConfig:
        """スクレイパー設定モデルを取得"""
        return self._app_config.scraper
    
    @property
    def excel(self) -> ExcelConfig:
        """Excel出力設定モデルを取得"""
        return self._app_config.excel
    
    @property
    def processing(self) -> ProcessingConfig:
        """処理設定モデルを取得"""
        return self._app_config.processing
    
    @property
    def paths(self) -> PathsConfig:
        """パス設定モデルを取得"""
        return self._app_config.paths
    
    @property
    def cache(self) -> CacheConfig:
        """キャッシュ設定モデルを取得"""
        return self._app_config.cache
    
    @property
    def text(self) -> TextConfig:
        """テキスト出力設定モデルを取得"""
        return self._app_config.text
    
    @property
    def logging(self) -> LoggingConfig:
        """ロギング設定モデルを取得"""
        return self._app_config.logging
    
    def get_all_categories(self) -> List[str]:
        """
        テンプレートCSVから全カテゴリを取得
        
        Returns:
            カテゴリリスト
        """
        import pandas as pd
        
        try:
            template_path = self._app_config.paths.template_csv
            if not template_path.exists():
                logging.warning(f"テンプレートCSVが見つかりません: {template_path}")
                return []
            
            df = pd.read_csv(template_path)
            if 'category' not in df.columns:
                logging.warning("テンプレートCSVにcategoryカラムがありません")
                return []
            
            return df['category'].unique().tolist()
        except Exception as e:
            logging.error(f"カテゴリ取得エラー: {e}")
            return []
