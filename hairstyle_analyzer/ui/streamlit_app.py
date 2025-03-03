"""
Streamlitアプリケーションモジュール

このモジュールは、ヘアスタイル画像解析システムのStreamlit UIを提供します。
画像アップロード、分析実行、結果表示、エクセル出力などの機能を含みます。
"""

import os
import sys
import logging
import asyncio
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import streamlit as st
import pandas as pd
from PIL import Image

from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.services.gemini.gemini_service import GeminiService
from hairstyle_analyzer.services.scraper.scraper_service import ScraperService
from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.core.style_matching import StyleMatchingService
from hairstyle_analyzer.core.excel_exporter import ExcelExporter
from hairstyle_analyzer.core.processor import MainProcessor
from hairstyle_analyzer.utils.errors import AppError
from hairstyle_analyzer.ui.components.error_display import display_error, StreamlitErrorHandler


# セッションステート用キー
SESSION_PROCESSOR = "processor"
SESSION_CONFIG = "config"
SESSION_RESULTS = "results"
SESSION_API_KEY = "api_key"
SESSION_SALON_URL = "salon_url"
SESSION_PROGRESS = "progress"
SESSION_STYLISTS = "stylists"
SESSION_COUPONS = "coupons"


def init_session_state():
    """セッションステートを初期化"""
    # セッション変数の初期化
    if SESSION_RESULTS not in st.session_state:
        st.session_state[SESSION_RESULTS] = []
    
    if SESSION_PROGRESS not in st.session_state:
        st.session_state[SESSION_PROGRESS] = {
            "current": 0,
            "total": 0,
            "message": "",
            "start_time": None,
            "complete": False
        }
    
    if SESSION_STYLISTS not in st.session_state:
        st.session_state[SESSION_STYLISTS] = []
    
    if SESSION_COUPONS not in st.session_state:
        st.session_state[SESSION_COUPONS] = []


def update_progress(current, total, message=""):
    """進捗状況の更新"""
    if SESSION_PROGRESS in st.session_state:
        progress = st.session_state[SESSION_PROGRESS]
        progress["current"] = current
        progress["total"] = total
        progress["message"] = message
        
        # 完了時の処理
        if current >= total and total > 0:
            progress["complete"] = True
        
        st.session_state[SESSION_PROGRESS] = progress


async def process_images(processor, image_paths, progress_callback=None):
    """画像処理を実行する関数"""
    results = []
    total = len(image_paths)
    
    for i, image_path in enumerate(image_paths):
        try:
            # 1画像の処理
            result = await processor.process_single_image(image_path)
            results.append(result)
            
            # 進捗更新
            if progress_callback:
                progress_callback(i + 1, total)
                
        except Exception as e:
            logging.error(f"画像処理エラー ({image_path.name}): {str(e)}")
            # エラーを含む結果オブジェクトを追加することも可能
    
    return results


def create_processor(config_manager):
    """メインプロセッサーの作成"""
    # APIキーの取得（セッションまたは環境変数から）
    api_key = st.session_state.get(SESSION_API_KEY, "")
    
    # APIキーが指定されていればConfigManagerに設定
    if api_key:
        config_manager.save_api_key(api_key)
    
    # テンプレートマネージャーの初期化
    template_manager = TemplateManager(config_manager.paths.template_csv)
    
    # キャッシュマネージャーの初期化
    cache_manager = CacheManager(config_manager.paths.cache_file, config_manager.cache)
    
    # GeminiServiceの初期化
    gemini_service = GeminiService(config_manager.gemini)
    
    # 各コアコンポーネントの初期化
    image_analyzer = ImageAnalyzer(gemini_service, cache_manager)
    template_matcher = TemplateMatcher(template_manager)
    style_matcher = StyleMatchingService(gemini_service)
    excel_exporter = ExcelExporter(config_manager.excel)
    
    # メインプロセッサーの初期化
    processor = MainProcessor(
        image_analyzer=image_analyzer,
        template_matcher=template_matcher,
        style_matcher=style_matcher,
        excel_exporter=excel_exporter,
        cache_manager=cache_manager,
        batch_size=config_manager.processing.batch_size,
        api_delay=config_manager.processing.api_delay
    )
    
    return processor


def display_progress():
    """進捗状況の表示"""
    if SESSION_PROGRESS in st.session_state:
        progress = st.session_state[SESSION_PROGRESS]
        current = progress["current"]
        total = progress["total"]
        message = progress["message"]
        
        if total > 0:
            # プログレスバーの表示
            progress_val = min(current / total, 1.0)
            progress_bar = st.progress(progress_val)
            
            # 進捗メッセージの表示
            if message:
                st.write(f"状態: {message}")
            
            # 処理時間の表示
            if progress["start_time"]:
                elapsed = time.time() - progress["start_time"]
                if elapsed < 60:
                    st.write(f"経過時間: {elapsed:.1f}秒")
                else:
                    minutes = int(elapsed // 60)
                    seconds = int(elapsed % 60)
                    st.write(f"経過時間: {minutes}分{seconds}秒")
                
                # 残り時間の予測（現在の進捗から）
                if 0 < current < total:
                    remaining = (elapsed / current) * (total - current)
                    if remaining < 60:
                        st.write(f"推定残り時間: {remaining:.1f}秒")
                    else:
                        minutes = int(remaining // 60)
                        seconds = int(remaining % 60)
                        st.write(f"推定残り時間: {minutes}分{seconds}秒")
            
            # 完了メッセージ
            if progress["complete"]:
                st.success(f"処理が完了しました: {current}/{total}画像")


def display_results(results):
    """処理結果を表示する関数"""
    if not results:
        st.warning("表示する結果がありません。")
        return
    
    st.subheader("処理結果")
    
    # 結果データをDataFrameに変換
    data = []
    for result in results:
        data.append({
            "画像": result.image_name,
            "カテゴリ": result.style_analysis.category,
            "性別": result.attribute_analysis.sex,
            "長さ": result.attribute_analysis.length,
            "タイトル": result.selected_template.title,
            "スタイリスト": result.selected_stylist.name,
            "クーポン": result.selected_coupon.name
        })
    
    df = pd.DataFrame(data)
    
    # データフレームを表示
    st.dataframe(df)
    
    # Excel出力ボタン
    if st.button("Excel出力"):
        try:
            # セッションにプロセッサーがなければ作成
            if SESSION_PROCESSOR not in st.session_state:
                config_manager = get_config_manager()
                st.session_state[SESSION_PROCESSOR] = create_processor(config_manager)
            
            processor = st.session_state[SESSION_PROCESSOR]
            
            # Excel生成
            excel_bytes = processor.export_to_excel(results)
            
            # ダウンロードボタンを表示
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hairstyle_analysis_{timestamp}.xlsx"
            
            st.download_button(
                label="Excelファイルをダウンロード",
                data=excel_bytes,
                file_name=filename,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            display_error(e)
            st.error(f"Excel出力中にエラーが発生しました: {str(e)}")


async def fetch_salon_data(url, config_manager):
    """サロンのスタイリストとクーポン情報を取得"""
    try:
        # スクレイパーキャッシュパス
        cache_path = Path("cache") / "scraper_cache.json"
        cache_path.parent.mkdir(exist_ok=True)
        
        # スクレイパーの初期化
        async with ScraperService(config_manager.scraper, cache_path) as scraper:
            st.write("サロンデータを取得中...")
            progress_bar = st.progress(0.0)
            
            for i in range(10):
                # 進捗表示（ダミー）
                progress_bar.progress((i + 1) / 10)
                if i < 9:  # 最後の繰り返しでは待機しない
                    await asyncio.sleep(0.1)
            
            # スタイリストとクーポン情報の取得
            stylists, coupons = await scraper.fetch_all_data(url)
            
            # 結果保存
            st.session_state[SESSION_STYLISTS] = stylists
            st.session_state[SESSION_COUPONS] = coupons
            
            st.success(f"サロンデータを取得しました: {len(stylists)}人のスタイリスト, {len(coupons)}件のクーポン")
            progress_bar.empty()
            
            return stylists, coupons
    except Exception as e:
        st.error(f"サロンデータの取得中にエラーが発生しました: {str(e)}")
        return [], []


def render_sidebar(config_manager):
    """サイドバーの表示"""
    with st.sidebar:
        st.title("設定")
        
        # APIキー設定
        st.header("API設定")
        api_key = st.text_input(
            "Gemini API Key",
            value=st.session_state.get(SESSION_API_KEY, config_manager.gemini.api_key),
            type="password",
            help="Google AI StudioからGemini APIキーを取得してください。"
        )
        
        # APIキーをセッションに保存
        if api_key:
            st.session_state[SESSION_API_KEY] = api_key
        
        # サロン設定
        st.header("サロン設定")
        salon_url = st.text_input(
            "ホットペッパービューティURL",
            value=st.session_state.get(SESSION_SALON_URL, config_manager.scraper.base_url),
            help="サロンのホットペッパービューティURLを入力してください。"
        )
        
        # URLをセッションに保存
        if salon_url:
            st.session_state[SESSION_SALON_URL] = salon_url
        
        # サロンデータ取得ボタン
        if st.button("サロンデータを取得"):
            # URLの検証
            if not salon_url or not salon_url.startswith("https://beauty.hotpepper.jp/"):
                st.error("有効なホットペッパービューティURLを入力してください。")
            else:
                # 非同期でサロンデータを取得
                asyncio.run(fetch_salon_data(salon_url, config_manager))
        
        # スタイリストとクーポン情報を表示
        if SESSION_STYLISTS in st.session_state and SESSION_COUPONS in st.session_state:
            stylists = st.session_state[SESSION_STYLISTS]
            coupons = st.session_state[SESSION_COUPONS]
            
            if stylists:
                st.write(f"スタイリスト: {len(stylists)}人")
                stylist_expander = st.expander("スタイリスト一覧")
                with stylist_expander:
                    for i, stylist in enumerate(stylists[:10]):  # 表示数を制限
                        st.write(f"{i+1}. {stylist.name}")
                    if len(stylists) > 10:
                        st.write(f"...他 {len(stylists) - 10}人")
            
            if coupons:
                st.write(f"クーポン: {len(coupons)}件")
                coupon_expander = st.expander("クーポン一覧")
                with coupon_expander:
                    for i, coupon in enumerate(coupons[:10]):  # 表示数を制限
                        st.write(f"{i+1}. {coupon.name}")
                    if len(coupons) > 10:
                        st.write(f"...他 {len(coupons) - 10}件")
        
        # 詳細設定セクション
        st.header("詳細設定")
        with st.expander("詳細設定"):
            # バッチサイズ設定
            batch_size = st.slider(
                "バッチサイズ",
                min_value=1,
                max_value=10,
                value=config_manager.processing.batch_size,
                help="一度に処理する画像の数です。大きすぎるとメモリ不足になる可能性があります。"
            )
            
            # API遅延設定
            api_delay = st.slider(
                "API遅延（秒）",
                min_value=0.1,
                max_value=5.0,
                value=config_manager.processing.api_delay,
                step=0.1,
                help="API呼び出し間の遅延時間です。小さすぎるとレート制限に達する可能性があります。"
            )
            
            # キャッシュTTL設定
            cache_ttl_days = st.slider(
                "キャッシュ有効期間（日）",
                min_value=1,
                max_value=30,
                value=config_manager.cache.ttl_days,
                help="キャッシュの有効期間です。長すぎると古い結果が返される可能性があります。"
            )
            
            # 設定を保存
            if st.button("設定を保存"):
                try:
                    # 設定の更新
                    config_updates = {
                        "processing": {
                            "batch_size": batch_size,
                            "api_delay": api_delay
                        },
                        "cache": {
                            "ttl_days": cache_ttl_days
                        }
                    }
                    
                    # スクレイパーURLの更新
                    if salon_url:
                        config_updates["scraper"] = {
                            "base_url": salon_url
                        }
                    
                    # 設定の更新
                    config_manager.update_config(config_updates)
                    
                    # APIキーの保存
                    if api_key:
                        config_manager.save_api_key(api_key)
                    
                    st.success("設定を保存しました。")
                
                except Exception as e:
                    st.error(f"設定の保存中にエラーが発生しました: {str(e)}")
        
        # キャッシュクリアボタン
        st.header("キャッシュ管理")
        if st.button("キャッシュをクリア"):
            try:
                # キャッシュマネージャーの初期化
                cache_manager = CacheManager(config_manager.paths.cache_file, config_manager.cache)
                
                # キャッシュクリア
                cleared_count = cache_manager.clear()
                
                st.success(f"キャッシュをクリアしました: {cleared_count}件のエントリが削除されました")
            except Exception as e:
                st.error(f"キャッシュのクリア中にエラーが発生しました: {str(e)}")


def render_main_content():
    """メインコンテンツの表示"""
    st.title("ヘアスタイル分析システム")
    
    # 説明テキスト
    st.markdown("""
    このアプリケーションは、ヘアスタイル画像を分析し、最適なタイトル、説明、スタイリスト、クーポンを提案します。
    画像をアップロードして「タイトル生成」ボタンをクリックしてください。
    """)
    
    # 画像アップロード部分
    uploaded_files = st.file_uploader(
        "ヘアスタイル画像をアップロードしてください",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True,
        help="PNG, JPG, JPEGフォーマットの画像ファイルをアップロードできます。"
    )
    
    # アップロードされた画像のプレビュー表示
    if uploaded_files:
        st.write(f"{len(uploaded_files)}枚の画像がアップロードされました")
        
        # 画像プレビューを表示（横に並べる）
        cols = st.columns(min(3, len(uploaded_files)))
        for i, uploaded_file in enumerate(uploaded_files[:6]):  # 最大6枚まで表示
            with cols[i % 3]:
                st.image(uploaded_file, caption=uploaded_file.name, use_column_width=True)
        
        # 6枚以上の場合は省略メッセージを表示
        if len(uploaded_files) > 6:
            st.write(f"他 {len(uploaded_files) - 6} 枚の画像は省略されています")
        
        # 処理開始ボタン
        if st.button("タイトル生成", type="primary"):
            # セッションにプロセッサーがなければ作成
            if SESSION_PROCESSOR not in st.session_state:
                config_manager = get_config_manager()
                st.session_state[SESSION_PROCESSOR] = create_processor(config_manager)
            
            # 一時ディレクトリに画像を保存
            temp_dir = Path("temp")
            temp_dir.mkdir(exist_ok=True)
            image_paths = []
            
            for uploaded_file in uploaded_files:
                # ファイル名を安全に処理
                safe_filename = ''.join(c for c in uploaded_file.name if c.isalnum() or c in '._- ').replace(' ', '_')
                temp_path = temp_dir / safe_filename
                
                # 画像を一時ファイルとして保存
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                image_paths.append(temp_path)
            
            # プログレスバーの表示
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # 初期化
                processor = st.session_state[SESSION_PROCESSOR]
                
                # 非同期処理を実行
                with st.spinner("画像を処理中..."):
                    # 進捗コールバック関数
                    def update_progress(current, total):
                        progress = float(current) / float(total)
                        progress_bar.progress(progress)
                        status_text.text(f"処理中: {current}/{total} ({int(progress * 100)}%)")
                    
                    # 処理の実行
                    results = asyncio.run(process_images(processor, image_paths, update_progress))
                    
                    # 処理完了
                    progress_bar.progress(1.0)
                    status_text.text("処理完了!")
                    
                    # 結果をセッションに保存
                    st.session_state[SESSION_RESULTS] = results
                    
                    # 結果表示
                    display_results(results)
            
            except Exception as e:
                display_error(e)
                st.error(f"処理中にエラーが発生しました: {str(e)}")
    
    # 結果が既にセッションにある場合は表示
    elif SESSION_RESULTS in st.session_state:
        display_results(st.session_state[SESSION_RESULTS])


def get_config_manager():
    """設定マネージャーのインスタンスを取得する"""
    # セッションから取得を試みる
    if SESSION_CONFIG in st.session_state:
        return st.session_state[SESSION_CONFIG]
    
    # セッションになければ新規作成
    config_manager = ConfigManager("config/config.yaml")
    st.session_state[SESSION_CONFIG] = config_manager
    return config_manager


def run_streamlit_app(config_manager: ConfigManager):
    """
    Streamlitアプリケーションを実行する
    
    Args:
        config_manager: 設定マネージャー
    """
    # セッションの初期化
    init_session_state()
    
    # セッションに設定マネージャーを保存
    st.session_state[SESSION_CONFIG] = config_manager
    
    # ページ設定
    st.set_page_config(
        page_title="ヘアスタイル画像解析システム",
        page_icon="💇",
        layout="wide",
    )
    
    # サイドバーの表示
    render_sidebar(config_manager)
    
    # メインコンテンツ
    render_main_content()
    
    # フッター
    st.write("---")
    st.write("© 2025 Hairstyle Analyzer System")


if __name__ == "__main__":
    # 設定マネージャーの初期化
    config_manager = ConfigManager("config/config.yaml")
    
    # アプリケーションの実行
    run_streamlit_app(config_manager)
