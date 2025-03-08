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

# 環境変数の設定
os.environ["PYTHONIOENCODING"] = "utf-8"

# セッションキー
SESSION_SALON_URL = "salon_url"
SESSION_PROCESSOR = "processor"
SESSION_RESULTS = "results"
SESSION_STYLISTS = "stylists"
SESSION_COUPONS = "coupons"
SESSION_PROGRESS = "progress"
SESSION_USE_CACHE = "use_cache"
SESSION_CONFIG = "config"

# モジュールのインポート
from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.data.template_manager import TemplateManager
from hairstyle_analyzer.data.cache_manager import CacheManager
from hairstyle_analyzer.services.scraper.scraper_service import ScraperService

# コアモジュール
from hairstyle_analyzer.core.template_matcher import TemplateMatcher
from hairstyle_analyzer.core.image_analyzer import ImageAnalyzer
from hairstyle_analyzer.core.style_matching import StyleMatchingService
from hairstyle_analyzer.core.excel_exporter import ExcelExporter
from hairstyle_analyzer.core.processor import MainProcessor

# 新しいアーキテクチャに関連するインポート
# ※これらのモジュールパスが現在の構造と一致しない場合は、コメントアウトし、必要に応じて修正します
# from hairstyle_analyzer.services.gemini_service import GeminiService
# from hairstyle_analyzer.analyzer.style_analyzer import StyleAnalyzer
# from hairstyle_analyzer.analyzer.attribute_analyzer import AttributeAnalyzer
# from hairstyle_analyzer.expert.matchmaking_expert import MatchmakingExpert
# from hairstyle_analyzer.recommender.style_recommender import StyleRecommender
# from hairstyle_analyzer.processor.style_processor import StyleProcessor

# 実際に使用可能なインポート（上記の代替として）
from hairstyle_analyzer.services.gemini.gemini_service import GeminiService

# UI コンポーネント
from hairstyle_analyzer.utils.async_context import progress_tracker

from hairstyle_analyzer.data.models import ProcessResult, StyleAnalysis, AttributeAnalysis, Template, StylistInfo, CouponInfo


def init_session_state():
    """セッションステートを初期化"""
    # セッション変数の初期化
    if SESSION_PROCESSOR not in st.session_state:
        st.session_state[SESSION_PROCESSOR] = None
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
    if SESSION_USE_CACHE not in st.session_state:
        st.session_state[SESSION_USE_CACHE] = True
    # APIキーのセッション変数初期化は削除
    if SESSION_SALON_URL not in st.session_state:
        st.session_state[SESSION_SALON_URL] = ""


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


async def process_images(processor, image_paths, stylists=None, coupons=None, use_cache=True):
    """画像を処理して結果を取得する非同期関数"""
    results = []
    total = len(image_paths)
    
    # プロセッサーがNoneの場合、再初期化を試みる
    if processor is None:
        logging.error("プロセッサーがNoneのため、再初期化を試みます")
        try:
            config_manager = get_config_manager()
            processor = create_processor(config_manager)
            if processor is None:
                logging.error("プロセッサーの再初期化に失敗しました")
                return []
            # 再初期化が成功した場合、セッションに保存
            st.session_state[SESSION_PROCESSOR] = processor
            logging.info("プロセッサーの再初期化に成功し、セッションに保存しました")
        except Exception as e:
            logging.error(f"プロセッサーの再初期化中にエラーが発生: {str(e)}")
            return []
    
    # 画像が存在するか確認
    if not image_paths:
        logging.error("画像パスが空です")
        return []
    
    # 進捗状況の初期化
    progress = {
        "current": 0,
        "total": total,
        "message": "初期化中...",
        "start_time": time.time(),
        "complete": False
    }
    st.session_state[SESSION_PROGRESS] = progress
    
    try:
        # キャッシュ設定を適用
        processor.use_cache = use_cache
        
        # 各画像を処理
        for i, image_path in enumerate(image_paths):
            try:
                # 進捗状況の更新
                progress["current"] = i
                progress["message"] = f"画像 {i+1}/{total} を処理中..."
                st.session_state[SESSION_PROGRESS] = progress
                
                # 文字列パスをPathオブジェクトに変換
                path_obj = Path(image_path) if isinstance(image_path, str) else image_path
                
                # ログに記録
                image_name = path_obj.name
                logging.info(f"画像 {image_name} の処理を開始します")
                
                # 画像処理
                if stylists and coupons:
                    # スタイリストとクーポンのデータを渡して処理
                    result = await processor.process_single_image(path_obj, stylists, coupons, use_cache=use_cache)
                else:
                    # 基本処理
                    result = await processor.process_single_image(path_obj, use_cache=use_cache)
                
                # 結果にファイル名を追加
                if result:
                    if isinstance(result, dict) and 'image_name' not in result:
                        result['image_name'] = image_name
                        result['image_path'] = str(path_obj)
                    results.append(result)
                
            except Exception as e:
                # 個別の画像処理中のエラーをログに記録（処理は続行）
                logging.error(f"画像処理エラー ({image_name}): {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                continue
        
        # 進捗状況の更新
        progress["current"] = total
        progress["message"] = "処理完了"
        progress["complete"] = True
        st.session_state[SESSION_PROGRESS] = progress
        
        return results
    
    except Exception as e:
        # 全体の処理中のエラーをログに記録
        logging.error(f"画像処理全体でエラーが発生: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return []


def create_processor(config_manager):
    """プロセッサーを作成する関数"""
    try:
        logging.info("プロセッサーの作成を開始します")
        
        # 設定マネージャーがNoneの場合の対応
        if config_manager is None:
            logging.error("設定マネージャーがNoneです")
            return None
        
        # テンプレートマネージャーの初期化
        template_manager = TemplateManager(config_manager.paths.template_csv)
        logging.info(f"テンプレートファイル: {config_manager.paths.template_csv}")
        
        # テンプレートマネージャーの初期化確認
        if not template_manager:
            logging.error("テンプレートマネージャーの初期化に失敗しました")
            return None
        
        # キャッシュマネージャーの初期化
        cache_manager = CacheManager(config_manager.paths.cache_file, config_manager.cache)
        logging.info(f"キャッシュファイル: {config_manager.paths.cache_file}")
        
        # APIキーの確認と取得
        api_key = get_api_key()
        if not api_key:
            logging.warning("APIキーが設定されていません。画像処理は機能しません。")
        
        # GeminiServiceの初期化（APIキーを直接コンストラクタに渡す）
        # コンフィグにAPIキーを設定
        config_manager.gemini.api_key = api_key
        
        # APIキーを含むコンフィグでGeminiServiceを初期化
        gemini_service = GeminiService(config_manager.gemini)
        logging.info(f"Gemini API設定: モデル={config_manager.gemini.model}")
        
        # 各コアコンポーネントの初期化
        image_analyzer = ImageAnalyzer(gemini_service, cache_manager)
        template_matcher = TemplateMatcher(template_manager)
        style_matcher = StyleMatchingService(gemini_service)
        excel_exporter = ExcelExporter(config_manager.excel)
        
        # キャッシュ使用設定の取得
        use_cache = st.session_state.get(SESSION_USE_CACHE, True)
        logging.info(f"キャッシュ使用設定: {use_cache}")
        
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
        
        logging.info("プロセッサーの作成が完了しました")
        return processor
        
    except Exception as e:
        # エラーの詳細をログに記録
        logging.error(f"プロセッサー作成中にエラーが発生: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return None


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
                    comment = selected_template.get('comment', '')
                    menu = selected_template.get('menu', '')
                    hashtag = selected_template.get('hashtag', '')
                else:
                    title = getattr(selected_template, 'title', '')
                    comment = getattr(selected_template, 'comment', '')
                    menu = getattr(selected_template, 'menu', '')
                    hashtag = getattr(selected_template, 'hashtag', '')
                
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
                comment = getattr(result.selected_template, 'comment', '')
                menu = getattr(result.selected_template, 'menu', '')
                hashtag = getattr(result.selected_template, 'hashtag', '')
                stylist_name = getattr(result.selected_stylist, 'name', '')
                coupon_name = getattr(result.selected_coupon, 'name', '')
            
            # データの追加 - Excelと同じ順序で表示
            data.append({
                "スタイリスト名": stylist_name,
                "クーポン名": coupon_name,
                "コメント": comment,
                "スタイルタイトル": title,
                "性別": sex,
                "長さ": length,
                "スタイルメニュー": menu,
                "ハッシュタグ": hashtag,
                "画像ファイル名": image_name
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
    """サロンデータの取得"""
    if not url:
        st.warning("サロンURLを入力してください")
        return None, None
    
    # キャッシュディレクトリの設定
    cache_dir = Path(os.environ.get("CACHE_DIR", "cache"))
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "scraper_cache.json"
    
    try:
        # スクレイパーサービスの初期化
        async with ScraperService(
            config=config_manager.scraper,
            cache_path=cache_path
        ) as scraper:
            st.write("サロンデータを取得中...")
            progress_bar = st.progress(0.0)
            
            # スタイリストとクーポン情報の取得
            stylists, coupons = await scraper.fetch_all_data(url)
            
            # 結果保存
            st.session_state[SESSION_STYLISTS] = stylists
            st.session_state[SESSION_COUPONS] = coupons
            
            progress_bar.progress(1.0)
            st.success(f"スタイリスト{len(stylists)}名、クーポン{len(coupons)}件のデータを取得しました。")
            
            return stylists, coupons
        
    except Exception as e:
        st.error(f"サロンデータの取得中にエラーが発生しました: {str(e)}")
        return None, None


def render_sidebar(config_manager):
    """サイドバーの表示"""
    with st.sidebar:
        st.title("設定")
        
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
                    
                    st.success("設定を保存しました。")
                
                except Exception as e:
                    st.error(f"設定の保存中にエラーが発生しました: {str(e)}")
        
        # キャッシュ管理セクション
        st.header("キャッシュ管理")
        
        # キャッシュ使用設定
        use_cache = st.checkbox(
            "キャッシュを使用する",
            value=st.session_state.get(SESSION_USE_CACHE, True),
            help="オフにすると毎回APIリクエストを実行します。テスト時などに有用です。"
        )
        
        # キャッシュ使用設定をセッションに保存
        st.session_state[SESSION_USE_CACHE] = use_cache
        
        # プロセッサーがすでに存在する場合は設定を更新
        if SESSION_PROCESSOR in st.session_state and st.session_state[SESSION_PROCESSOR] is not None:
            processor = st.session_state[SESSION_PROCESSOR]
            processor.set_use_cache(use_cache)
            st.session_state[SESSION_PROCESSOR] = processor
        

def convert_to_process_results(results):
    """結果をProcessResultオブジェクトに変換する関数"""
    from hairstyle_analyzer.core.processor import ProcessResult
    
    process_results = []
    for result in results:
        if isinstance(result, dict):
            # 辞書の場合はProcessResultオブジェクトに変換
            image_path = result.get("image_path", "")
            title = result.get("title", "")
            template_id = result.get("template_id", "")
            template_name = result.get("template_name", "")
            stylist_name = result.get("stylist_name", "")
            coupon_name = result.get("coupon_name", "")
            analysis_results = result.get("analysis_results", {})
            
            process_result = ProcessResult(
                image_path=image_path,
                title=title,
                template_id=template_id,
                template_name=template_name,
                stylist_name=stylist_name,
                coupon_name=coupon_name,
                analysis_results=analysis_results
            )
            
            process_results.append(process_result)
        else:
            # すでにProcessResultオブジェクトの場合はそのまま追加
            process_results.append(result)
    
    return process_results

def generate_excel_download(processor, results, title="タイトル生成が完了しました。"):
    """プロセッサーを使用してExcelファイルを生成し、ダウンロードボタンを表示する関数"""
    try:
        # プロセッサーの結果をクリア
        processor.clear_results()
        
        # 結果をProcessResultオブジェクトに変換してプロセッサーに追加
        process_results = convert_to_process_results(results)
        processor.results.extend(process_results)
        
        # Excelバイナリデータを取得
        excel_bytes = processor.get_excel_binary()
        
        # Excelファイルの生成
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"hairstyle_analysis_{timestamp}.xlsx"
        
        # 通知メッセージとダウンロードボタンを表示
        st.success(f"{title}下のボタンをクリックしてExcelファイルをダウンロードしてください。")
        
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
        
        return True
    
    except Exception as e:
        logging.error(f"Excel出力中にエラーが発生しました: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        st.error(f"Excel出力中にエラーが発生しました: {str(e)}")
        return False

def render_main_content():
    """メインコンテンツを表示する関数"""
    
    # 必要な関数をローカルスコープにインポート（名前解決エラー回避のため）
    from hairstyle_analyzer.ui.streamlit_app import convert_to_process_results, generate_excel_download
    
    # タイトル表示
    st.write("# 🔍 ヘアスタイル画像解析システム")
    
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
        
        # 画像プレビューを表示（横に並べる）- 列数を4に増やし、画像サイズを制限
        cols = st.columns(min(4, len(uploaded_files)))
        for i, uploaded_file in enumerate(uploaded_files[:8]):  # 最大8枚まで表示
            with cols[i % 4]:
                # 画像を開いてリサイズ
                image = Image.open(uploaded_file)
                # 画像の最大幅を200pxに制限
                st.image(image, caption=uploaded_file.name, width=200)
        
        # 8枚以上の場合は省略メッセージを表示
        if len(uploaded_files) > 8:
            st.write(f"他 {len(uploaded_files) - 8} 枚の画像は省略されています")
        
        # 処理開始ボタン
        if st.button("タイトル生成", type="primary"):
            # セッションからプロセッサーを取得または初期化
            try:
                # プロセッサーが存在するか確認
                if SESSION_PROCESSOR not in st.session_state or st.session_state[SESSION_PROCESSOR] is None:
                    logging.info("プロセッサーがセッションに存在しないため、新規作成します")
                    config_manager = get_config_manager()
                    processor = create_processor(config_manager)
                    
                    # 初期化に成功したか確認
                    if processor is None:
                        st.error("プロセッサーの初期化に失敗しました。ログを確認してください。")
                        return
                    
                    # セッションに保存
                    st.session_state[SESSION_PROCESSOR] = processor
                    logging.info("プロセッサーを初期化してセッションに保存しました")
                else:
                    processor = st.session_state[SESSION_PROCESSOR]
                    logging.info("セッションからプロセッサーを取得しました")
                
                # 一時ディレクトリに画像を保存
                temp_dir = Path(os.environ.get("TEMP_DIR", "temp")) / "hairstyle_analyzer"
                temp_dir.mkdir(parents=True, exist_ok=True)
                image_paths = handle_image_upload(uploaded_files)
                
                if not image_paths:
                    st.error("画像の保存中にエラーが発生しました。")
                    return
                
                logging.info(f"{len(image_paths)}枚の画像を一時ディレクトリに保存しました")
                
                # プログレスバーの表示
                progress_bar = st.progress(0)
                status_text = st.empty()
                
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
                    use_cache = st.session_state.get(SESSION_USE_CACHE, True)
                    
                    # 処理の実行（スタイリストとクーポンのデータとキャッシュ設定を渡す）
                    results = asyncio.run(process_images(processor, image_paths, stylists, coupons, use_cache))
                    
                    # 処理完了
                    progress_bar.progress(1.0)
                    status_text.text("処理完了！")
                    
                    # 結果が空でないか確認
                    if not results:
                        st.error("画像処理中にエラーが発生しました。ログを確認してください。")
                        return
                    
                    # 結果をセッションに保存
                    st.session_state[SESSION_RESULTS] = results
                    
                    # 結果表示
                    display_results(results)
                    
                    # ここからExcel出力処理を追加
                    try:
                        # プロセッサーがセッションに存在することを確認
                        processor = st.session_state[SESSION_PROCESSOR]
                        
                        # Excel出力とダウンロードボタン表示
                        generate_excel_download(processor, results, "タイトル生成が完了しました。")
                    
                    except Exception as e:
                        logging.error(f"Excel出力中にエラーが発生しました: {str(e)}")
                        import traceback
                        logging.error(traceback.format_exc())
                        st.error(f"Excel出力中にエラーが発生しました: {str(e)}")
            
            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {str(e)}")
                logging.error(f"処理中にエラーが発生しました: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
    
    # 結果が既にセッションにある場合は表示
    elif SESSION_RESULTS in st.session_state and st.session_state[SESSION_RESULTS]:
        results = st.session_state[SESSION_RESULTS]
        display_results(results)
        
        # プロセッサーがセッションに存在するか確認
        if SESSION_PROCESSOR in st.session_state and st.session_state[SESSION_PROCESSOR] is not None:
            try:
                # セッションからプロセッサーを取得
                processor = st.session_state[SESSION_PROCESSOR]
                
                # Excel出力とダウンロードボタン表示
                generate_excel_download(processor, results, "以前の処理結果からExcelファイルを生成できます。")
                
            except Exception as e:
                logging.error(f"既存結果からのExcel出力中にエラーが発生しました: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                st.error(f"Excel出力中にエラーが発生しました: {str(e)}")


def get_config_manager():
    """設定マネージャーのインスタンスを取得する"""
    # セッションから取得を試みる
    if SESSION_CONFIG in st.session_state:
        return st.session_state[SESSION_CONFIG]
    
    # セッションになければ新規作成
    config_manager = ConfigManager("config/config.yaml")
    st.session_state[SESSION_CONFIG] = config_manager
    return config_manager


def handle_image_upload(uploaded_files):
    """アップロードされた画像ファイルを一時ディレクトリに保存する関数"""
    if not uploaded_files:
        return []
    
    try:
        # 一時ディレクトリの作成
        temp_dir = Path(os.environ.get("TEMP_DIR", "temp")) / "hairstyle_analyzer"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        # 前回の一時ファイルをクリーンアップ
        try:
            for old_file in temp_dir.glob("*"):
                if old_file.is_file():
                    old_file.unlink()
            logging.info("前回の一時ファイルをクリーンアップしました")
        except Exception as e:
            logging.warning(f"一時ファイルのクリーンアップ中にエラー: {str(e)}")
        
        # 画像ファイルの保存
        image_paths = []
        for i, file in enumerate(uploaded_files):
            try:
                # ファイル名の取得（拡張子を含む）
                original_filename = file.name
                file_ext = Path(original_filename).suffix.lower()
                
                # ファイル拡張子の検証
                if file_ext not in ['.jpg', '.jpeg', '.png']:
                    logging.warning(f"サポートされていないファイル形式: {file_ext}")
                    continue
                
                # 安全なファイル名の生成
                safe_filename = f"styleimg_{i+1}{file_ext}"
                temp_path = temp_dir / safe_filename
                
                # ファイルの保存
                with open(temp_path, "wb") as f:
                    f.write(file.getbuffer())
                
                # 画像の検証
                try:
                    img = Image.open(temp_path)
                    img.verify()  # 画像が有効か検証
                    img.close()
                    # 再度開いてサイズを確認
                    with Image.open(temp_path) as img:
                        width, height = img.size
                        if width <= 0 or height <= 0:
                            logging.warning(f"無効な画像サイズ: {width}x{height}, ファイル: {safe_filename}")
                            continue
                        logging.info(f"画像サイズ: {width}x{height}, ファイル: {safe_filename}")
                except Exception as e:
                    logging.error(f"画像検証エラー ({safe_filename}): {str(e)}")
                    continue
                
                # 成功した場合、パスをリストに追加（文字列として）
                image_paths.append(str(temp_path))
                logging.info(f"画像を保存しました: {original_filename} -> {safe_filename}")
                
            except Exception as e:
                logging.error(f"画像アップロードエラー: {str(e)}")
                import traceback
                logging.error(traceback.format_exc())
                continue
        
        return image_paths
        
    except Exception as e:
        logging.error(f"画像のアップロード全体でエラーが発生: {str(e)}")
        import traceback
        logging.error(traceback.format_exc())
        return []


def get_api_key():
    """APIキーを取得する関数"""
    try:
        # 環境変数からの取得を最初に試みる（.envファイルから）
        if "GEMINI_API_KEY" in os.environ:
            api_key = os.environ["GEMINI_API_KEY"]
            logging.info("環境変数からのキー取得: 成功")
            return api_key
            
        # Streamlit Secretsからの取得を試みる（抑制された警告で）
        # シークレットの存在を事前にチェック
        secrets_path = Path(".streamlit/secrets.toml")
        home_secrets_path = Path.home() / ".streamlit/secrets.toml"
        
        if secrets_path.exists() or home_secrets_path.exists():
            # シークレットファイルが存在する場合のみアクセスを試みる
            try:
                if "GEMINI_API_KEY" in st.secrets:
                    api_key = st.secrets["GEMINI_API_KEY"]
                    logging.info("Streamlit Secretsからのキー取得: 成功")
                    return api_key
            except Exception as e:
                # シークレットアクセスのエラーは抑制する（ログのみ）
                logging.debug(f"シークレットアクセス中の例外（無視します）: {str(e)}")
        else:
            # シークレットファイルが存在しない場合はデバッグログのみ
            logging.debug("secrets.tomlファイルが見つかりません。環境変数のみを使用します。")
        
        # APIキーが見つからなかった場合の処理
        logging.warning("APIキーが設定されていません。.envファイルでGEMINI_API_KEYを設定してください。")
        return None
            
    except Exception as e:
        logging.error(f"APIキー取得中にエラーが発生: {str(e)}")
        return None


def run_streamlit_app(config_manager: ConfigManager, skip_page_config: bool = False):
    """
    Streamlitアプリケーションを実行する
    
    Args:
        config_manager: 設定マネージャー
        skip_page_config: Trueの場合、ページ設定（st.set_page_config）をスキップする
    """
    # セッションの初期化
    init_session_state()
    
    # セッションに設定マネージャーを保存
    st.session_state[SESSION_CONFIG] = config_manager
    
    # ページ設定（skip_page_configがFalseの場合のみ実行）
    if not skip_page_config:
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

# エラーハンドリング関数
def display_error(e):
    """エラーをログに記録し、ユーザーに表示する"""
    error_message = f"エラーが発生しました: {str(e)}"
    logging.error(error_message)
    st.error(error_message)


class StreamlitErrorHandler:
    """Streamlit用のエラーハンドラークラス"""
    def __init__(self):
        self.error_occurred = False
        self.error_message = ""
    
    def __enter__(self):
        self.error_occurred = False
        self.error_message = ""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.error_occurred = True
            self.error_message = str(exc_val)
            logging.error(f"エラーが発生: {exc_type.__name__}: {exc_val}")
            import traceback
            logging.error(traceback.format_exc())
            st.error(f"エラーが発生しました: {exc_val}")
            return True  # 例外を処理済みとする
        return False
