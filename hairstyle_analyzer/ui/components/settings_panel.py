"""
設定パネルコンポーネントモジュール

このモジュールでは、アプリケーションの設定を行うためのパネルコンポーネントを提供します。
API設定、サロン設定、詳細設定などの入力フォームが含まれます。
"""

import logging
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Union, List, Tuple

from ...data.config_manager import ConfigManager
from ...utils.errors import ConfigError


class SettingsPanelComponent:
    """
    設定パネルコンポーネント
    
    アプリケーションの設定を行うためのパネルコンポーネントを提供します。
    API設定、サロン設定、詳細設定などの入力フォームが含まれます。
    """
    
    def __init__(self, config_manager: ConfigManager):
        """
        初期化
        
        Args:
            config_manager: 設定マネージャー
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = config_manager
    
    def display_settings_sidebar(self, 
                              on_save: Optional[Callable[[], None]] = None, 
                              on_clear_cache: Optional[Callable[[], None]] = None) -> Dict[str, Any]:
        """
        サイドバーに設定パネルを表示します
        
        Args:
            on_save: 設定保存時のコールバック関数（オプション）
            on_clear_cache: キャッシュクリア時のコールバック関数（オプション）
            
        Returns:
            更新された設定値の辞書
        """
        st.sidebar.title("設定")
        
        # 設定値の取得
        settings = {}
        
        # API設定セクション
        st.sidebar.header("API設定")
        
        # Gemini API設定
        api_key = st.sidebar.text_input(
            "Gemini API Key",
            value=self.config_manager.gemini.api_key,
            type="password",
            help="Google AI StudioからGemini APIキーを取得してください。"
        )
        settings["gemini_api_key"] = api_key
        
        # モデル選択
        model_options = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro"]
        selected_model = st.sidebar.selectbox(
            "使用するモデル",
            options=model_options,
            index=model_options.index(self.config_manager.gemini.model) if self.config_manager.gemini.model in model_options else 0,
            help="画像分析に使用するGeminiモデルを選択します。"
        )
        settings["gemini_model"] = selected_model
        
        # サロン設定セクション
        st.sidebar.header("サロン設定")
        
        # HotPepper Beauty URL
        salon_url = st.sidebar.text_input(
            "HotPepper Beauty URL",
            value=self.config_manager.scraper.base_url,
            help="ホットペッパービューティーのサロンURLを入力してください。"
        )
        settings["salon_url"] = salon_url
        
        # 詳細設定セクション（折りたたみ可能）
        with st.sidebar.expander("詳細設定", expanded=False):
            # 処理設定
            st.markdown("##### 処理設定")
            
            # バッチサイズ
            batch_size = st.slider(
                "バッチサイズ",
                min_value=1,
                max_value=20,
                value=self.config_manager.processing.batch_size,
                help="一度に処理する画像の数を設定します。システムリソースに応じて調整してください。"
            )
            settings["batch_size"] = batch_size
            
            # API遅延
            api_delay = st.slider(
                "API呼び出し間隔（秒）",
                min_value=0.0,
                max_value=5.0,
                value=self.config_manager.processing.api_delay,
                step=0.1,
                help="API呼び出し間の遅延時間を設定します。レート制限に対応するため、値を大きくしてください。"
            )
            settings["api_delay"] = api_delay
            
            # 最大リトライ回数
            max_retries = st.slider(
                "最大リトライ回数",
                min_value=0,
                max_value=10,
                value=self.config_manager.processing.max_retries,
                help="API呼び出し失敗時の最大リトライ回数を設定します。"
            )
            settings["max_retries"] = max_retries
            
            # キャッシュ設定
            st.markdown("##### キャッシュ設定")
            
            # キャッシュTTL
            cache_ttl = st.slider(
                "キャッシュ有効期限（日）",
                min_value=1,
                max_value=90,
                value=self.config_manager.cache.ttl_days,
                help="キャッシュの有効期限を日数で設定します。"
            )
            settings["cache_ttl"] = cache_ttl
            
            # キャッシュサイズ制限
            cache_size = st.slider(
                "最大キャッシュエントリ数",
                min_value=100,
                max_value=50000,
                value=self.config_manager.cache.max_size,
                step=100,
                help="キャッシュに保存する最大エントリ数を設定します。"
            )
            settings["cache_size"] = cache_size
            
            # 出力設定
            st.markdown("##### 出力設定")
            
            # 出力ディレクトリ
            output_dir = st.text_input(
                "出力ディレクトリ",
                value=str(self.config_manager.paths.output_excel.parent),
                help="Excel出力を保存するディレクトリを設定します。"
            )
            settings["output_dir"] = output_dir
            
            # 出力ファイル名
            output_filename = st.text_input(
                "出力ファイル名",
                value=self.config_manager.paths.output_excel.name,
                help="出力するExcelファイルの名前を設定します。"
            )
            settings["output_filename"] = output_filename
        
        # 設定の保存ボタン
        if st.sidebar.button("設定を保存", type="primary"):
            try:
                # API設定の更新
                if api_key:
                    self.config_manager.save_api_key(api_key)
                
                # その他の設定を更新
                config_updates = {
                    "gemini": {
                        "model": selected_model
                    },
                    "scraper": {
                        "base_url": salon_url
                    },
                    "processing": {
                        "batch_size": batch_size,
                        "api_delay": api_delay,
                        "max_retries": max_retries
                    },
                    "cache": {
                        "ttl_days": cache_ttl,
                        "max_size": cache_size
                    },
                    "paths": {
                        "output_excel": str(Path(output_dir) / output_filename)
                    }
                }
                
                self.config_manager.update_config(config_updates)
                st.sidebar.success("設定を保存しました。")
                
                # コールバック関数の呼び出し
                if on_save:
                    on_save()
                    
            except ConfigError as e:
                st.sidebar.error(f"設定の保存に失敗しました: {str(e)}")
                self.logger.error(f"設定保存エラー: {str(e)}")
        
        # キャッシュクリアボタン
        if st.sidebar.button("キャッシュをクリア"):
            try:
                # コールバック関数の呼び出し
                if on_clear_cache:
                    on_clear_cache()
                st.sidebar.success("キャッシュをクリアしました。")
            except Exception as e:
                st.sidebar.error(f"キャッシュのクリアに失敗しました: {str(e)}")
                self.logger.error(f"キャッシュクリアエラー: {str(e)}")
        
        return settings
    
    def display_advanced_settings(self) -> Dict[str, Any]:
        """
        詳細設定パネルを表示します
        
        Returns:
            更新された詳細設定値の辞書
        """
        st.title("詳細設定")
        
        advanced_settings = {}
        
        # タブで設定を整理
        tabs = st.tabs(["API設定", "処理設定", "スクレイピング設定", "出力設定", "キャッシュ設定"])
        
        # API設定タブ
        with tabs[0]:
            st.header("Gemini API設定")
            
            # 温度パラメータ
            temperature = st.slider(
                "温度パラメータ",
                min_value=0.0,
                max_value=1.0,
                value=self.config_manager.gemini.temperature,
                step=0.05,
                help="生成の多様性を制御します。低い値ではより決定論的な応答に、高い値ではよりランダムな応答になります。"
            )
            advanced_settings["gemini_temperature"] = temperature
            
            # 最大トークン数
            max_tokens = st.slider(
                "最大トークン数",
                min_value=100,
                max_value=1000,
                value=self.config_manager.gemini.max_tokens,
                step=50,
                help="生成する最大トークン数を設定します。"
            )
            advanced_settings["gemini_max_tokens"] = max_tokens
            
            # カスタムプロンプトテンプレート
            st.subheader("プロンプトテンプレート")
            
            # プロンプトテンプレート編集（折りたたみ可能）
            with st.expander("カスタムプロンプトテンプレート", expanded=False):
                prompt_template = st.text_area(
                    "分析プロンプトテンプレート",
                    value=self.config_manager.gemini.prompt_template,
                    height=300,
                    help="画像分析用のプロンプトテンプレートをカスタマイズできます。"
                )
                advanced_settings["prompt_template"] = prompt_template
                
                attribute_prompt_template = st.text_area(
                    "属性分析プロンプトテンプレート",
                    value=self.config_manager.gemini.attribute_prompt_template,
                    height=200,
                    help="性別・髪の長さ分析用のプロンプトテンプレートをカスタマイズできます。"
                )
                advanced_settings["attribute_prompt_template"] = attribute_prompt_template
        
        # 処理設定タブ
        with tabs[1]:
            st.header("処理設定")
            
            # リトライ設定
            st.subheader("リトライ設定")
            
            retry_delay = st.slider(
                "リトライ間隔（秒）",
                min_value=0.5,
                max_value=10.0,
                value=self.config_manager.processing.retry_delay,
                step=0.5,
                help="リトライ間の待機時間を設定します。"
            )
            advanced_settings["retry_delay"] = retry_delay
            
            # メモリ使用量
            memory_per_image = st.slider(
                "画像あたりのメモリ使用量（MB）",
                min_value=1,
                max_value=50,
                value=self.config_manager.processing.memory_per_image_mb,
                help="処理時の画像あたりの推定メモリ使用量を設定します。"
            )
            advanced_settings["memory_per_image_mb"] = memory_per_image
        
        # スクレイピング設定タブ
        with tabs[2]:
            st.header("スクレイピング設定")
            
            # タイムアウト設定
            timeout = st.slider(
                "リクエストタイムアウト（秒）",
                min_value=5,
                max_value=60,
                value=self.config_manager.scraper.timeout,
                help="スクレイピングリクエストのタイムアウト時間を設定します。"
            )
            advanced_settings["scraper_timeout"] = timeout
            
            # クーポンページ設定
            coupon_page_limit = st.slider(
                "クーポンページ数上限",
                min_value=1,
                max_value=10,
                value=self.config_manager.scraper.coupon_page_limit,
                help="取得するクーポンページの最大数を設定します。"
            )
            advanced_settings["coupon_page_limit"] = coupon_page_limit
            
            # 詳細設定（上級者向け）
            with st.expander("上級者向け設定", expanded=False):
                st.warning("これらの設定を変更すると、スクレイピングが正常に動作しなくなる可能性があります。")
                
                stylist_link_selector = st.text_input(
                    "スタイリストリンクセレクタ",
                    value=self.config_manager.scraper.stylist_link_selector,
                    help="スタイリストリンクを特定するためのCSSセレクタを設定します。"
                )
                advanced_settings["stylist_link_selector"] = stylist_link_selector
                
                stylist_name_selector = st.text_input(
                    "スタイリスト名セレクタ",
                    value=self.config_manager.scraper.stylist_name_selector,
                    help="スタイリスト名を特定するためのCSSセレクタを設定します。"
                )
                advanced_settings["stylist_name_selector"] = stylist_name_selector
                
                coupon_class_name = st.text_input(
                    "クーポン名クラス名",
                    value=self.config_manager.scraper.coupon_class_name,
                    help="クーポン名を特定するためのHTMLクラス名を設定します。"
                )
                advanced_settings["coupon_class_name"] = coupon_class_name
        
        # 出力設定タブ
        with tabs[3]:
            st.header("Excel出力設定")
            
            # ヘッダー設定
            st.subheader("ヘッダー設定")
            
            excel_headers = self.config_manager.excel.headers
            columns = ["A", "B", "C", "D", "E", "F", "G", "H", "I"]
            
            custom_headers = {}
            
            for col in columns:
                default_value = excel_headers.get(col, "")
                custom_header = st.text_input(
                    f"{col}列のヘッダー",
                    value=default_value,
                    key=f"header_{col}"
                )
                custom_headers[col] = custom_header
            
            advanced_settings["excel_headers"] = custom_headers
        
        # キャッシュ設定タブ
        with tabs[4]:
            st.header("キャッシュ設定")
            
            # キャッシュファイルパス
            cache_file = st.text_input(
                "キャッシュファイルパス",
                value=str(self.config_manager.paths.cache_file),
                help="キャッシュファイルのパスを設定します。"
            )
            advanced_settings["cache_file"] = cache_file
            
            # キャッシュの表示
            if st.button("キャッシュ統計を表示"):
                # キャッシュマネージャーが利用可能な場合のみ
                try:
                    from ...data.cache_manager import CacheManager
                    
                    cache_config = self.config_manager.cache
                    cache_manager = CacheManager(self.config_manager.paths.cache_file, cache_config)
                    
                    stats = cache_manager.get_statistics()
                    
                    st.subheader("キャッシュ統計")
                    st.write(f"合計エントリ数: {stats['total_entries']}")
                    st.write(f"有効なエントリ数: {stats['valid_entries']}")
                    st.write(f"期限切れのエントリ数: {stats['expired_entries']}")
                    st.write(f"キャッシュサイズ制限: {stats['size_limit']}")
                    st.write(f"TTL (日): {stats['ttl_days']}")
                    
                    if stats['oldest_entry_timestamp'] > 0:
                        oldest_date = datetime.fromtimestamp(stats['oldest_entry_timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        st.write(f"最も古いエントリ: {oldest_date}")
                    
                    if stats['newest_entry_timestamp'] > 0:
                        newest_date = datetime.fromtimestamp(stats['newest_entry_timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        st.write(f"最も新しいエントリ: {newest_date}")
                        
                except Exception as e:
                    st.error(f"キャッシュ統計の取得に失敗しました: {str(e)}")
        
        # 設定の保存ボタン
        if st.button("詳細設定を保存", type="primary"):
            try:
                # 詳細設定の更新
                config_updates = {
                    "gemini": {
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "prompt_template": prompt_template,
                        "attribute_prompt_template": attribute_prompt_template
                    },
                    "scraper": {
                        "timeout": timeout,
                        "coupon_page_limit": coupon_page_limit,
                        "stylist_link_selector": stylist_link_selector,
                        "stylist_name_selector": stylist_name_selector,
                        "coupon_class_name": coupon_class_name
                    },
                    "processing": {
                        "retry_delay": retry_delay,
                        "memory_per_image_mb": memory_per_image
                    },
                    "excel": {
                        "headers": custom_headers
                    },
                    "paths": {
                        "cache_file": cache_file
                    }
                }
                
                self.config_manager.update_config(config_updates)
                st.success("詳細設定を保存しました。")
                    
            except ConfigError as e:
                st.error(f"詳細設定の保存に失敗しました: {str(e)}")
                self.logger.error(f"詳細設定保存エラー: {str(e)}")
        
        return advanced_settings
