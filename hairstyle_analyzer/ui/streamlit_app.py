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
SESSION_USE_CACHE = "use_cache"


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


async def process_images(processor, image_paths, stylists=None, coupons=None, progress_callback=None, use_cache=None):
    """画像処理を実行する関数
    
    Args:
        processor: メインプロセッサー
        image_paths: 画像ファイルのパスリスト
        stylists: スタイリスト情報のリスト（オプション）
        coupons: クーポン情報のリスト（オプション）
        progress_callback: 進捗コールバック関数（オプション）
        use_cache: キャッシュを使用するかどうか（Noneの場合はプロセッサーの設定を使用）
    
    Returns:
        処理結果のリスト
    """
    results = []
    total = len(image_paths)
    
    for i, image_path in enumerate(image_paths):
        try:
            # 1画像の処理（スタイリストとクーポンのデータを渡す）
            if stylists and coupons:
                result = await processor.process_single_image(image_path, stylists, coupons, use_cache=use_cache)
            else:
                result = await processor.process_single_image(image_path, use_cache=use_cache)
            
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
    
    # キャッシュ使用設定の取得
    use_cache = st.session_state.get(SESSION_USE_CACHE, False)
    
    # 各コアコンポーネントの初期化
    image_analyzer = ImageAnalyzer(gemini_service, cache_manager, use_cache=use_cache)
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
        api_delay=config_manager.processing.api_delay,
        use_cache=use_cache
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
        # 結果が辞書型かオブジェクト型か確認
        try:
            if isinstance(result, dict):
                # 辞書型の場合
                image_name = result.get('image_name', '不明')
                
                # style_analysisの取得
                style_analysis = result.get('style_analysis', {})
                if isinstance(style_analysis, dict):
                    category = style_analysis.get('category', '')
                else:
                    category = getattr(style_analysis, 'category', '')
                
                # attribute_analysisの取得
                attribute_analysis = result.get('attribute_analysis', {})
                if isinstance(attribute_analysis, dict):
                    sex = attribute_analysis.get('sex', '')
                    length = attribute_analysis.get('length', '')
                else:
                    sex = getattr(attribute_analysis, 'sex', '')
                    length = getattr(attribute_analysis, 'length', '')
                
                # selected_templateの取得
                selected_template = result.get('selected_template', {})
                if isinstance(selected_template, dict):
                    title = selected_template.get('title', '')
                else:
                    title = getattr(selected_template, 'title', '')
                
                # selected_stylistの取得
                selected_stylist = result.get('selected_stylist', {})
                if isinstance(selected_stylist, dict):
                    stylist_name = selected_stylist.get('name', '')
                else:
                    stylist_name = getattr(selected_stylist, 'name', '')
                
                # selected_couponの取得
                selected_coupon = result.get('selected_coupon', {})
                if isinstance(selected_coupon, dict):
                    coupon_name = selected_coupon.get('name', '')
                else:
                    coupon_name = getattr(selected_coupon, 'name', '')
            else:
                # オブジェクト型の場合
                image_name = getattr(result, 'image_name', '不明')
                category = getattr(result.style_analysis, 'category', '')
                sex = getattr(result.attribute_analysis, 'sex', '')
                length = getattr(result.attribute_analysis, 'length', '')
                title = getattr(result.selected_template, 'title', '')
                stylist_name = getattr(result.selected_stylist, 'name', '')
                coupon_name = getattr(result.selected_coupon, 'name', '')
            
            # データの追加
            data.append({
                "画像": image_name,
                "カテゴリ": category,
                "性別": sex,
                "長さ": length,
                "タイトル": title,
                "スタイリスト": stylist_name,
                "クーポン": coupon_name
            })
        except Exception as e:
            st.error(f"結果の処理中にエラーが発生しました: {str(e)}")
            st.write(f"結果の形式: {type(result)}")
            if isinstance(result, dict):
                st.write(f"結果のキー: {list(result.keys())}")
    
    df = pd.DataFrame(data)
    
    # 概要データフレームを表示
    st.write("### 結果概要")
    st.dataframe(df)
    
    # 詳細情報をエクスパンダーで表示
    st.write("### 詳細情報")
    
    # 各画像ごとにエクスパンダーを作成
    for result in results:
        # 画像名を取得
        if isinstance(result, dict):
            image_name = result.get('image_name', '不明')
        else:
            image_name = getattr(result, 'image_name', '不明')
        
        # エクスパンダーを作成（デフォルトで閉じた状態）
        with st.expander(f"📷 {image_name}", expanded=False):
            # 3列レイアウトで表示
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.write("#### 基本情報")
                
                # スタイル分析結果
                if isinstance(result, dict):
                    style_analysis = result.get('style_analysis', {})
                    if isinstance(style_analysis, dict):
                        category = style_analysis.get('category', '')
                        features = style_analysis.get('features', {})
                    else:
                        category = getattr(style_analysis, 'category', '')
                        features = getattr(style_analysis, 'features', None)
                    
                    # 属性分析結果
                    attribute_analysis = result.get('attribute_analysis', {})
                    if isinstance(attribute_analysis, dict):
                        sex = attribute_analysis.get('sex', '')
                        length = attribute_analysis.get('length', '')
                    else:
                        sex = getattr(attribute_analysis, 'sex', '')
                        length = getattr(attribute_analysis, 'length', '')
                else:
                    category = getattr(result.style_analysis, 'category', '')
                    features = getattr(result.style_analysis, 'features', None)
                    sex = getattr(result.attribute_analysis, 'sex', '')
                    length = getattr(result.attribute_analysis, 'length', '')
                
                st.write(f"**カテゴリ:** {category}")
                st.write(f"**性別:** {sex}")
                st.write(f"**長さ:** {length}")
                
                # 特徴の詳細表示
                st.write("#### スタイル特徴")
                if features:
                    if isinstance(features, dict):
                        for key, value in features.items():
                            st.write(f"**{key}:** {value}")
                    else:
                        st.write(f"**色:** {getattr(features, 'color', '')}")
                        st.write(f"**カット技法:** {getattr(features, 'cut_technique', '')}")
                        st.write(f"**スタイリング:** {getattr(features, 'styling', '')}")
                        st.write(f"**印象:** {getattr(features, 'impression', '')}")
            
            with col2:
                st.write("#### スタイリスト情報")
                
                # スタイリスト情報
                if isinstance(result, dict):
                    stylist = result.get('selected_stylist', {})
                    if isinstance(stylist, dict):
                        stylist_name = stylist.get('name', '')
                        specialties = stylist.get('specialties', '')
                        description = stylist.get('description', '')
                    else:
                        stylist_name = getattr(stylist, 'name', '')
                        specialties = getattr(stylist, 'specialties', '')
                        description = getattr(stylist, 'description', '')
                    
                    # スタイリスト選択理由
                    stylist_reason = result.get('stylist_reason', '')
                else:
                    stylist_name = getattr(result.selected_stylist, 'name', '')
                    specialties = getattr(result.selected_stylist, 'specialties', '')
                    description = getattr(result.selected_stylist, 'description', '')
                    stylist_reason = getattr(result, 'stylist_reason', None)
                
                st.write(f"**スタイリスト名:** {stylist_name}")
                st.write(f"**得意な技術・特徴:** {specialties}")
                st.write(f"**説明文:** {description}")
                
                # 選択理由を表示
                st.write("#### 選択理由")
                st.write(stylist_reason or "選択理由は記録されていません")
            
            with col3:
                st.write("#### クーポン情報")
                
                # クーポン情報
                if isinstance(result, dict):
                    coupon = result.get('selected_coupon', {})
                    if isinstance(coupon, dict):
                        coupon_name = coupon.get('name', '')
                        price = coupon.get('price', 0)
                        description = coupon.get('description', '')
                    else:
                        coupon_name = getattr(coupon, 'name', '')
                        price = getattr(coupon, 'price', 0)
                        description = getattr(coupon, 'description', '')
                    
                    # クーポン選択理由
                    coupon_reason = result.get('coupon_reason', '')
                else:
                    coupon_name = getattr(result.selected_coupon, 'name', '')
                    price = getattr(result.selected_coupon, 'price', 0)
                    description = getattr(result.selected_coupon, 'description', '')
                    coupon_reason = getattr(result, 'coupon_reason', None)
                
                st.write(f"**クーポン名:** {coupon_name}")
                st.write(f"**価格:** {price}円")
                st.write(f"**説明:** {description}")
                
                # 選択理由を表示
                st.write("#### 選択理由")
                st.write(coupon_reason or "選択理由は記録されていません")
            

    



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
        
        # キャッシュ管理セクション
        st.header("キャッシュ管理")
        
        # キャッシュ使用設定
        use_cache = st.checkbox(
            "キャッシュを使用する", 
            value=st.session_state.get(SESSION_USE_CACHE, False),
            help="チェックすると、以前の分析結果をキャッシュから取得します。新しい分析結果が必要な場合はオフにしてください。"
        )
        
        # キャッシュ使用設定をセッションに保存
        st.session_state[SESSION_USE_CACHE] = use_cache
        
        # プロセッサーがすでに存在する場合は設定を更新
        if SESSION_PROCESSOR in st.session_state and st.session_state[SESSION_PROCESSOR] is not None:
            processor = st.session_state[SESSION_PROCESSOR]
            processor.set_use_cache(use_cache)
            st.session_state[SESSION_PROCESSOR] = processor
        

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
                st.image(uploaded_file, caption=uploaded_file.name, use_container_width=True)
        
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
                    
                    # スタイリストとクーポンのデータを取得
                    stylists = st.session_state.get(SESSION_STYLISTS, [])
                    coupons = st.session_state.get(SESSION_COUPONS, [])
                    
                    # スタイリストとクーポンのデータが存在するか確認
                    if not stylists:
                        st.warning("スタイリスト情報が取得されていません。サイドバーの「サロンデータを取得」ボタンを押してデータを取得してください。")
                    if not coupons:
                        st.warning("クーポン情報が取得されていません。サイドバーの「サロンデータを取得」ボタンを押してデータを取得してください。")
                    
                    # キャッシュ使用設定の取得
                    use_cache = st.session_state.get(SESSION_USE_CACHE, False)
                    
                    # 処理の実行（スタイリストとクーポンのデータとキャッシュ設定を渡す）
                    results = asyncio.run(process_images(processor, image_paths, stylists, coupons, update_progress, use_cache=use_cache))
                    
                    # 処理完了
                    progress_bar.progress(1.0)
                    status_text.text("処理完了!")
                    
                    # 結果をセッションに保存
                    st.session_state[SESSION_RESULTS] = results
                    
                    # 結果表示
                    display_results(results)
                    
                    # 自動Excel出力処理
                    try:
                        # セッションにプロセッサーがなければ作成
                        if SESSION_PROCESSOR not in st.session_state:
                            config_manager = get_config_manager()
                            st.session_state[SESSION_PROCESSOR] = create_processor(config_manager)
                        
                        processor = st.session_state[SESSION_PROCESSOR]
                        
                        # Excel生成
                        # 処理結果をプロセッサーに設定
                        processor.clear_results()
                        
                        # 結果をプロセッサーに追加する前に、辞書型の場合はProcessResultオブジェクトに変換
                        from hairstyle_analyzer.data.models import ProcessResult, StyleAnalysis, AttributeAnalysis, Template, StylistInfo, CouponInfo
                        from datetime import datetime
                        
                        for result in results:
                            if isinstance(result, dict):
                                # 辞書型の場合、ProcessResultオブジェクトに変換
                                
                                # style_analysisの取得と変換
                                style_analysis_dict = result.get('style_analysis', {})
                                if isinstance(style_analysis_dict, dict):
                                    style_analysis = StyleAnalysis(
                                        category=style_analysis_dict.get('category', ''),
                                        features=style_analysis_dict.get('features', []),
                                        colors=style_analysis_dict.get('colors', []),
                                        textures=style_analysis_dict.get('textures', [])
                                    )
                                else:
                                    style_analysis = style_analysis_dict
                                
                                # attribute_analysisの取得と変換
                                attribute_analysis_dict = result.get('attribute_analysis', {})
                                if isinstance(attribute_analysis_dict, dict):
                                    attribute_analysis = AttributeAnalysis(
                                        sex=attribute_analysis_dict.get('sex', ''),
                                        length=attribute_analysis_dict.get('length', '')
                                    )
                                else:
                                    attribute_analysis = attribute_analysis_dict
                                
                                # selected_templateの取得と変換
                                template_dict = result.get('selected_template', {})
                                if isinstance(template_dict, dict):
                                    template = Template(
                                        category=template_dict.get('category', ''),
                                        title=template_dict.get('title', ''),
                                        menu=template_dict.get('menu', ''),
                                        comment=template_dict.get('comment', ''),
                                        hashtag=template_dict.get('hashtag', '')
                                    )
                                else:
                                    template = template_dict
                                
                                # selected_stylistの取得と変換
                                stylist_dict = result.get('selected_stylist', {})
                                if isinstance(stylist_dict, dict):
                                    stylist = StylistInfo(
                                        name=stylist_dict.get('name', ''),
                                        specialties=stylist_dict.get('specialties', ''),
                                        description=stylist_dict.get('description', '')
                                    )
                                else:
                                    stylist = stylist_dict
                                
                                # selected_couponの取得と変換
                                coupon_dict = result.get('selected_coupon', {})
                                if isinstance(coupon_dict, dict):
                                    coupon = CouponInfo(
                                        name=coupon_dict.get('name', ''),
                                        price=coupon_dict.get('price', 0),
                                        description=coupon_dict.get('description', ''),
                                        categories=coupon_dict.get('categories', []),
                                        conditions=coupon_dict.get('conditions', {})
                                    )
                                else:
                                    coupon = coupon_dict
                                
                                # ProcessResultオブジェクトの作成
                                process_result = ProcessResult(
                                    image_name=result.get('image_name', '不明'),
                                    style_analysis=style_analysis,
                                    attribute_analysis=attribute_analysis,
                                    selected_template=template,
                                    selected_stylist=stylist,
                                    selected_coupon=coupon,
                                    processed_at=result.get('processed_at', datetime.now())
                                )
                                
                                processor.results.append(process_result)
                            else:
                                # すでにProcessResultオブジェクトの場合はそのまま追加
                                processor.results.append(result)
                        
                        # Excelバイナリデータを取得
                        excel_bytes = processor.get_excel_binary()
                        
                        # Excelファイルの生成
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"hairstyle_analysis_{timestamp}.xlsx"
                        
                        # 通知メッセージとダウンロードボタンを表示
                        st.success("タイトル生成が完了しました。下のボタンをクリックしてExcelファイルをダウンロードしてください。")
                        
                        # 目立つスタイルでダウンロードボタンを表示
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.download_button(
                                label="⬇️ Excelファイルをダウンロード ⬇️",
                                data=excel_bytes,
                                file_name=filename,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                help="クリックしてExcelファイルをダウンロード",
                                type="primary",
                                use_container_width=True
                            )
                            
                        # 少しスペースを追加
                        st.write("")
                        
                        # 自動ダウンロードの代わりに、目立つダウンロードボタンを表示
                        
                    except Exception as e:
                        display_error(e)
                        st.error(f"Excel出力中にエラーが発生しました: {str(e)}")
            
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
