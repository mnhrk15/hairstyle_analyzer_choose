"""
結果表示コンポーネントモジュール

このモジュールでは、ヘアスタイル分析の処理結果を表示するためのコンポーネントを提供します。
テーブル表示、詳細表示、フィルタリング、ソート機能などが含まれます。
"""

import logging
import streamlit as st
import pandas as pd
from typing import List, Dict, Any, Optional, Callable, Union
import base64
from datetime import datetime

from ...data.models import ProcessResult


class ResultsDisplayComponent:
    """
    処理結果表示コンポーネント
    
    ヘアスタイル分析の処理結果をテーブル形式で表示し、詳細表示、フィルタリング、ソート機能を提供します。
    """
    
    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)
    
    def display_results_table(self, results: List[ProcessResult], 
                            allow_filtering: bool = True,
                            allow_sorting: bool = True) -> None:
        """
        処理結果をテーブル形式で表示します
        
        Args:
            results: 処理結果のリスト
            allow_filtering: フィルタリングを許可するかどうか
            allow_sorting: ソートを許可するかどうか
        """
        if not results:
            st.info("表示する結果がありません。")
            return
        
        # 結果をDataFrameに変換
        data = []
        for result in results:
            data.append({
                "画像": result.image_name,
                "カテゴリ": result.style_analysis.category,
                "性別": result.attribute_analysis.sex,
                "髪の長さ": result.attribute_analysis.length,
                "スタイルタイトル": result.selected_template.title,
                "スタイリスト": result.selected_stylist.name,
                "クーポン": result.selected_coupon.name,
                "処理日時": result.processed_at.strftime("%Y-%m-%d %H:%M:%S") if result.processed_at else "",
                "_index": id(result)  # 内部用インデックス
            })
        
        df = pd.DataFrame(data)
        
        # フィルタリング機能
        if allow_filtering:
            st.subheader("検索とフィルタリング")
            
            # 検索ボックス
            search_term = st.text_input("キーワード検索", "")
            
            # カテゴリフィルター
            categories = ["すべて"] + sorted(list(set(df["カテゴリ"].tolist())))
            selected_category = st.selectbox("カテゴリでフィルタ", categories)
            
            # フィルタリングの適用
            filtered_df = df.copy()
            
            if search_term:
                # 全ての列に検索語を適用
                mask = pd.Series(False, index=filtered_df.index)
                for col in filtered_df.columns:
                    if col != "_index":  # 内部インデックスは除外
                        mask = mask | filtered_df[col].astype(str).str.contains(search_term, case=False, na=False)
                filtered_df = filtered_df[mask]
            
            if selected_category != "すべて":
                filtered_df = filtered_df[filtered_df["カテゴリ"] == selected_category]
            
            display_df = filtered_df
        else:
            display_df = df
        
        # ソート機能
        if allow_sorting:
            st.subheader("表示設定")
            
            # ソート列の選択
            sortable_columns = [col for col in display_df.columns if col != "_index"]
            sort_column = st.selectbox("ソート列", sortable_columns)
            
            # ソート順の選択
            sort_order = st.radio("ソート順", ["昇順", "降順"], horizontal=True)
            
            # ソートの適用
            ascending = sort_order == "昇順"
            display_df = display_df.sort_values(by=sort_column, ascending=ascending)
        
        # 表示列の選択（_indexは除外）
        display_columns = [col for col in display_df.columns if col != "_index"]
        
        # 件数表示
        st.write(f"合計: {len(display_df)} 件")
        
        # テーブル表示
        st.dataframe(display_df[display_columns], use_container_width=True)
        
        # 表示する結果の詳細ボタン
        if not display_df.empty:
            st.subheader("詳細表示")
            
            # 選択する行のインデックスを取得
            index_map = {i: idx for i, idx in enumerate(display_df["_index"].tolist())}
            selected_row = st.selectbox("詳細を表示する結果を選択", 
                                     range(len(display_df)),
                                     format_func=lambda i: display_df.iloc[i]["画像"])
            
            # 詳細表示ボタン
            if st.button("詳細を表示"):
                # 選択されたインデックスに対応する結果を見つける
                selected_index = index_map[selected_row]
                selected_result = next((r for r in results if id(r) == selected_index), None)
                
                if selected_result:
                    self.display_result_details(selected_result)
    
    def display_result_details(self, result: ProcessResult) -> None:
        """
        単一の処理結果の詳細を表示します
        
        Args:
            result: 処理結果
        """
        st.subheader(f"分析結果詳細: {result.image_name}")
        
        # タブで情報を整理
        tabs = st.tabs(["基本情報", "分析結果", "選択情報", "メタデータ"])
        
        # 基本情報タブ
        with tabs[0]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### 基本情報")
                st.markdown(f"**画像ファイル名:** {result.image_name}")
                st.markdown(f"**性別:** {result.attribute_analysis.sex}")
                st.markdown(f"**髪の長さ:** {result.attribute_analysis.length}")
                st.markdown(f"**カテゴリ:** {result.style_analysis.category}")
            
            with col2:
                st.markdown("##### 選択結果")
                st.markdown(f"**スタイルタイトル:** {result.selected_template.title}")
                st.markdown(f"**スタイルメニュー:** {result.selected_template.menu}")
                st.markdown(f"**スタイリスト:** {result.selected_stylist.name}")
                st.markdown(f"**クーポン:** {result.selected_coupon.name}")
        
        # 分析結果タブ
        with tabs[1]:
            st.markdown("##### スタイル分析結果")
            
            # 特徴を表示
            st.markdown("**特徴:**")
            features = result.style_analysis.features
            
            feature_data = {
                "項目": ["髪色", "カット技法", "スタイリング", "印象"],
                "内容": [
                    features.color,
                    features.cut_technique,
                    features.styling,
                    features.impression
                ]
            }
            
            st.table(pd.DataFrame(feature_data))
            
            # キーワードを表示
            st.markdown("**キーワード:**")
            keywords = result.style_analysis.keywords
            
            # キーワードをタグ風に表示
            keyword_html = " ".join([f'<span style="background-color: #e6f7ff; padding: 3px 8px; margin: 3px; border-radius: 10px;">{k}</span>' for k in keywords])
            st.markdown(keyword_html, unsafe_allow_html=True)
        
        # 選択情報タブ
        with tabs[2]:
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("##### テンプレート情報")
                template = result.selected_template
                
                st.markdown(f"**タイトル:** {template.title}")
                st.markdown(f"**カテゴリ:** {template.category}")
                st.markdown(f"**メニュー:** {template.menu}")
                
                st.markdown("**コメント:**")
                st.text_area("", template.comment, height=100, disabled=True)
                
                st.markdown("**ハッシュタグ:**")
                hashtags = template.hashtag.split(',')
                hashtag_html = " ".join([f'<span style="background-color: #f0f0f0; padding: 3px 8px; margin: 3px; border-radius: 10px;">#{tag.strip()}</span>' for tag in hashtags])
                st.markdown(hashtag_html, unsafe_allow_html=True)
            
            with col2:
                st.markdown("##### スタイリスト情報")
                stylist = result.selected_stylist
                
                st.markdown(f"**名前:** {stylist.name}")
                if stylist.position:
                    st.markdown(f"**役職:** {stylist.position}")
                
                st.markdown("**説明:**")
                st.text_area("", stylist.description, height=100, disabled=True)
                
                st.markdown("##### クーポン情報")
                coupon = result.selected_coupon
                
                st.markdown(f"**名前:** {coupon.name}")
                if coupon.price:
                    st.markdown(f"**価格:** {coupon.price}")
        
        # メタデータタブ
        with tabs[3]:
            st.markdown("##### 処理メタデータ")
            st.markdown(f"**処理日時:** {result.processed_at.strftime('%Y-%m-%d %H:%M:%S') if result.processed_at else '不明'}")
    
    def display_results_summary(self, results: List[ProcessResult]) -> None:
        """
        処理結果のサマリーを表示します
        
        Args:
            results: 処理結果のリスト
        """
        if not results:
            st.info("表示する結果がありません。")
            return
        
        st.subheader("分析結果サマリー")
        
        # 基本統計
        st.markdown(f"**処理画像数:** {len(results)}")
        
        # カテゴリ分布
        st.markdown("##### カテゴリ分布")
        categories = {}
        for result in results:
            category = result.style_analysis.category
            categories[category] = categories.get(category, 0) + 1
        
        category_df = pd.DataFrame({
            "カテゴリ": categories.keys(),
            "件数": categories.values()
        })
        
        st.bar_chart(category_df.set_index("カテゴリ"))
        
        # 性別分布
        st.markdown("##### 性別分布")
        genders = {}
        for result in results:
            gender = result.attribute_analysis.sex
            genders[gender] = genders.get(gender, 0) + 1
        
        gender_df = pd.DataFrame({
            "性別": genders.keys(),
            "件数": genders.values()
        })
        
        # 円グラフのためのデータ準備
        gender_names = list(genders.keys())
        gender_values = list(genders.values())
        
        # シンプルな表示
        st.table(gender_df)
        
        # 髪の長さ分布
        st.markdown("##### 髪の長さ分布")
        lengths = {}
        for result in results:
            length = result.attribute_analysis.length
            lengths[length] = lengths.get(length, 0) + 1
        
        length_df = pd.DataFrame({
            "髪の長さ": lengths.keys(),
            "件数": lengths.values()
        })
        
        st.bar_chart(length_df.set_index("髪の長さ"))
    
    def get_excel_download_button(self, 
                                excel_data: bytes, 
                                filename: str = "results.xlsx", 
                                button_text: str = "Excelをダウンロード") -> None:
        """
        Excel形式のデータをダウンロードするためのボタンを表示します
        
        Args:
            excel_data: Excelバイナリデータ
            filename: ダウンロードするファイル名
            button_text: ボタンに表示するテキスト
        """
        # Base64エンコード
        b64 = base64.b64encode(excel_data).decode()
        
        # ダウンロードリンクを作成
        href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}">{button_text}</a>'
        
        # ボタンを表示
        st.markdown(href, unsafe_allow_html=True)
