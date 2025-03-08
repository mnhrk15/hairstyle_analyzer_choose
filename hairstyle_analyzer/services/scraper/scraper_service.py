"""
スクレイパーサービスモジュール

このモジュールは、ホットペッパービューティサイトからスタイリストとクーポン情報を
スクレイピングするための機能を提供します。
"""

import logging
import asyncio
import re
import time
import json
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set, TypeVar, Callable
from urllib.parse import urlparse, urljoin, urlunparse, parse_qs, urlencode
from datetime import datetime, timedelta
from functools import wraps

import httpx
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from hairstyle_analyzer.data.models import ScraperConfig, StylistInfo, CouponInfo


class ScraperError(Exception):
    """スクレイピング関連のエラーの基底クラス"""
    def __init__(self, message: str, error_type: str = "SCRAPER_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_type = error_type
        self.details = details or {}
        super().__init__(self.message)


class NetworkError(ScraperError):
    """ネットワーク関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "NETWORK_ERROR", details)


class ParseError(ScraperError):
    """HTMLパース関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "PARSE_ERROR", details)


class ValidationError(ScraperError):
    """データ検証関連のエラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, "VALIDATION_ERROR", details)


class RateLimitError(NetworkError):
    """レート制限エラー"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_type = "RATE_LIMIT_ERROR"


class ScraperService:
    """
    ホットペッパービューティサイトのスクレイピングを行うサービスクラス
    
    このクラスは、ホットペッパービューティサイトからスタイリスト情報と
    クーポン情報を取得するための機能を提供します。
    """
    
    def __init__(self, config: ScraperConfig, cache_path: Optional[Path] = None):
        """
        ScraperServiceクラスの初期化
        
        Args:
            config: スクレイパーの設定
            cache_path: キャッシュファイルのパス（省略可）
        """
        self.logger = logging.getLogger(__name__)
        self.config = config
        self._client = None  # HTTPクライアントは遅延初期化
        self._cache = {}  # URLベースのキャッシュ
        self._cache_path = cache_path
        self._last_request_time = 0
        self._request_interval = 1.0  # リクエスト間隔（秒）
        self._semaphore = asyncio.Semaphore(5)  # 並列リクエスト数の制限
        
        # キャッシュの読み込み
        if self._cache_path and self._cache_path.exists():
            self._load_cache()
            
        self.logger.debug("ScraperServiceが初期化されました")
    
    async def initialize(self):
        """
        サービスの初期化を行います。
        HTTPクライアントの設定とその他の必要な初期化処理を実行します。
        """
        # HTTPクライアントの初期化
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self.config.timeout),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
            },
            follow_redirects=True
        )
        self.logger.info("ScraperService初期化完了 (ベースURL: %s)", self.config.base_url)
    
    async def close(self):
        """
        サービスのクリーンアップを行います。
        接続リソースの解放などを行います。
        """
        if self._client:
            await self._client.aclose()
            self._client = None
            
        # キャッシュの保存
        if self._cache_path:
            self._save_cache()
    
    async def __aenter__(self):
        """非同期コンテキストマネージャのエントリーポイント"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """非同期コンテキストマネージャの終了処理"""
        await self.close()
    
    def _load_cache(self):
        """キャッシュファイルから読み込みます"""
        try:
            with open(self._cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                
            # キャッシュの有効期限をチェック
            current_time = time.time()
            cache_ttl = 24 * 60 * 60  # 1日（秒単位）
            
            self._cache = {}
            for url, entry in cache_data.items():
                timestamp = entry.get('timestamp', 0)
                # 有効期限内のデータのみ読み込む
                if current_time - timestamp < cache_ttl:
                    self._cache[url] = entry
                    
            self.logger.info(f"{len(self._cache)}件のキャッシュを読み込みました")
        except Exception as e:
            self.logger.warning(f"キャッシュ読み込みエラー: {str(e)}")
            self._cache = {}
    
    def _save_cache(self):
        """キャッシュをファイルに保存します"""
        try:
            # ディレクトリが存在しない場合は作成
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._cache_path, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
                
            self.logger.info(f"{len(self._cache)}件のキャッシュを保存しました")
        except Exception as e:
            self.logger.warning(f"キャッシュ保存エラー: {str(e)}")

    async def validate_url(self, url: str) -> bool:
        """
        指定されたURLがホットペッパービューティのURLとして有効かどうかを検証します。
        
        Args:
            url: 検証するURL
            
        Returns:
            URLが有効な場合はTrue、そうでない場合はFalse
        """
        # URLの基本的な形式チェック
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                return False
            
            # ホットペッパービューティのドメインかチェック
            if not parsed_url.netloc.endswith("beauty.hotpepper.jp"):
                return False
            
            # サロンURLの形式チェック (/slnH000000000/ のような形式)
            if not re.search(r'/sln[A-Z][0-9]+/', parsed_url.path):
                return False
            
            return True
        except Exception as e:
            self.logger.warning(f"URL検証でエラーが発生しました: {str(e)}")
            return False
    
    async def _rate_limited_request(self, url: str) -> str:
        """
        レート制限付きのリクエストを行います。
        
        Args:
            url: リクエスト先URL
            
        Returns:
            レスポンスの内容
        """
        # キャッシュをチェック
        if url in self._cache:
            cache_entry = self._cache[url]
            current_time = time.time()
            # キャッシュ有効期限（1日）をチェック
            if current_time - cache_entry.get('timestamp', 0) < 24 * 60 * 60:
                self.logger.debug(f"キャッシュからデータを取得: {url}")
                return cache_entry['data']
        
        # レート制限
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._request_interval:
            delay = self._request_interval - elapsed
            await asyncio.sleep(delay)
        
        # セマフォによる並列数制限
        async with self._semaphore:
            self._last_request_time = time.time()
            response = await self._fetch_page(url)
            
            # キャッシュに保存
            self._cache[url] = {
                'data': response,
                'timestamp': time.time()
            }
            
            return response

    @retry(
        retry=retry_if_exception_type((NetworkError, RateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        reraise=True
    )
    async def _fetch_page(self, url: str) -> str:
        """
        指定されたURLのページを取得します。
        
        Args:
            url: 取得するページのURL
            
        Returns:
            ページのHTML内容
            
        Raises:
            NetworkError: ネットワーク関連のエラーが発生した場合
            RateLimitError: レート制限に達した場合
        """
        if not self._client:
            await self.initialize()
            
        try:
            response = await self._client.get(url)
            
            # レート制限のチェック
            if response.status_code == 429:
                # レート制限エラー
                retry_after = int(response.headers.get('Retry-After', 60))
                raise RateLimitError(
                    f"レート制限に達しました。{retry_after}秒後に再試行してください",
                    {"url": url, "retry_after": retry_after}
                )
                
            response.raise_for_status()
            return response.text
        except httpx.HTTPStatusError as e:
            raise NetworkError(f"HTTP エラー: {e.response.status_code}", {
                "url": url,
                "status_code": e.response.status_code
            })
        except httpx.RequestError as e:
            raise NetworkError(f"リクエストエラー: {str(e)}", {"url": url})
        except Exception as e:
            raise NetworkError(f"ページ取得中に予期しないエラーが発生しました: {str(e)}", {"url": url})

    def _parse_html(self, html_content: str) -> BeautifulSoup:
        """
        HTML文字列をBeautifulSoupオブジェクトに変換します。
        
        Args:
            html_content: HTML文字列
            
        Returns:
            BeautifulSoupオブジェクト
            
        Raises:
            ParseError: HTML解析中にエラーが発生した場合
        """
        try:
            return BeautifulSoup(html_content, 'html.parser')
        except Exception as e:
            raise ParseError(f"HTML解析エラー: {str(e)}")

    async def get_stylist_links(self, salon_url: str) -> List[dict]:
        """
        サロンページからスタイリスト情報とリンクを取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            スタイリスト情報の辞書リスト（名前、リンク、得意技術、説明文）
            
        Raises:
            NetworkError: ネットワーク関連のエラーが発生した場合
            ParseError: HTML解析中にエラーが発生した場合
        """
        self.logger.info(f"サロンページからスタイリスト情報を取得中: {salon_url}")
        
        # URLの検証
        if not await self.validate_url(salon_url):
            raise ValidationError(f"無効なサロンURL: {salon_url}")
        
        # ページの取得（レート制限・キャッシュ機能付き）
        stylist_page_url = salon_url + "stylist/"
        page_content = await self._rate_limited_request(stylist_page_url)
        soup = self._parse_html(page_content)
        
        # スタイリスト情報の取得
        stylist_info_list = []
        try:
            # テーブルの行を取得
            stylist_rows = soup.select("table.w756 tr")
            
            for row in stylist_rows:
                # 各セルを処理
                cells = row.select("td.vaT")
                for cell in cells:
                    # 名前
                    name_elem = cell.select_one("p.mT10.fs16.b > a")
                    if not name_elem:
                        continue
                    
                    name = name_elem.text.strip()
                    link = name_elem.get('href', '')
                    if link:
                        link = urljoin(salon_url, link)
                    
                    # 得意技術
                    specialties_elem = cell.select_one("div.mT5.fs10 > span.fgPink")
                    specialties = specialties_elem.text.strip() if specialties_elem else ""
                    
                    # 説明文
                    description_elem = cell.select_one("div.mT5.fs10.hMin30")
                    description = description_elem.text.strip() if description_elem else ""
                    
                    stylist_info = {
                        "name": name,
                        "link": link,
                        "specialties": specialties,
                        "description": description
                    }
                    
                    stylist_info_list.append(stylist_info)
            
            self.logger.info(f"{len(stylist_info_list)}人のスタイリスト情報を取得しました")
            return stylist_info_list
        except Exception as e:
            raise ParseError(f"スタイリスト情報取得エラー: {str(e)}", {
                "url": salon_url
            })

    async def get_stylist_info(self, stylist_data: dict) -> StylistInfo:
        """
        スタイリスト情報を作成します。
        
        Args:
            stylist_data: スタイリスト情報の辞書
            
        Returns:
            スタイリスト情報
        """
        self.logger.info(f"スタイリスト情報を作成: {stylist_data['name']}")
        
        stylist_info = StylistInfo(
            name=stylist_data["name"],
            specialties=stylist_data["specialties"],
            description=stylist_data["description"]
        )
        
        return stylist_info

    async def get_coupons(self, salon_url: str) -> List[CouponInfo]:
        """
        サロンページからクーポン情報を取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            クーポン情報のリスト
            
        Raises:
            NetworkError: ネットワーク関連のエラーが発生した場合
            ParseError: HTML解析中にエラーが発生した場合
        """
        self.logger.info(f"クーポン情報を取得中: {salon_url}")
        
        # URLの検証
        if not await self.validate_url(salon_url):
            raise ValidationError(f"無効なサロンURL: {salon_url}")
        
        # クーポンページのURL
        if not salon_url.endswith('/'):
            salon_url += '/'
        coupon_page_url = salon_url + "coupon/"
        
        # 実際のリクエストを行う前にURLが有効かチェック
        self.logger.info(f"クーポンページURL: {coupon_page_url}")
        
        # 全クーポンを格納するリスト
        all_coupons = []
        
        # 最初のページを処理
        page_content = await self._rate_limited_request(coupon_page_url)
        soup = self._parse_html(page_content)
        
        # 現在のページからクーポンを取得
        coupons = self._extract_coupons_from_page(soup)
        all_coupons.extend(coupons)
        self.logger.info(f"ページ 1 から {len(coupons)}件のクーポンを取得しました")
        
        # ページネーションを確認
        page_links = soup.select("p.pa.bottom0.right0")
        max_page = 1
        has_next_page = False
        next_page_url = None
        
        # ページネーション情報から最大ページ数を取得（例: "1/3ページ"）
        if page_links:
            pagination_text = page_links[0].get_text()
            self.logger.info(f"ページネーション情報: {pagination_text}")
            
            # "X/Yページ" の形式から最大ページ数を抽出
            pagination_match = re.search(r'(\d+)/(\d+)ページ', pagination_text)
            if pagination_match:
                current_page = int(pagination_match.group(1))
                total_pages = int(pagination_match.group(2))
                max_page = total_pages
                self.logger.info(f"ページネーション情報から最大ページ数を検出: {max_page}ページ")
        
        # "次へ"リンクを確認
        next_links = soup.select("p.pa.bottom0.right0 a.iS.arrowPagingR")
        if next_links:
            href = next_links[0].get("href", "")
            if href:
                has_next_page = True
                next_page_url = urljoin(coupon_page_url, href)
                self.logger.info(f"「次へ」リンクを検出: {next_page_url}")
        
        self.logger.info(f"検出された最大ページ数: {max_page}")
        
        # 2ページ目以降を処理
        for current_page in range(2, min(max_page + 1, self.config.coupon_page_limit + 1)):
            page_url = f"{coupon_page_url}PN{current_page}.html"
            
            try:
                self.logger.info(f"ページ {current_page}/{max_page} を処理中: {page_url}")
                page_content = await self._rate_limited_request(page_url)
                soup = self._parse_html(page_content)
                
                # 現在のページからクーポンを取得
                coupons = self._extract_coupons_from_page(soup)
                
                # クーポンが取得できなかった場合は警告を出すが処理は続行
                if not coupons:
                    self.logger.warning(f"ページ {current_page} にクーポンがありません。")
                
                self.logger.info(f"ページ {current_page} から {len(coupons)}件のクーポンを取得しました。現在の合計: {len(all_coupons) + len(coupons)}件")
                all_coupons.extend(coupons)
                
                # 最後のページに達したら終了
                if current_page == max_page:
                    self.logger.info(f"最大ページ数({max_page})に達しました。処理を終了します。")
                    break
                
            except Exception as e:
                self.logger.warning(f"ページ {current_page} の取得に失敗: {str(e)}")
                break
        
        self.logger.info(f"{len(all_coupons)}件のクーポン情報を取得しました")
        return all_coupons
    
    def _extract_coupons_from_page(self, soup: BeautifulSoup) -> List[CouponInfo]:
        """
        ページからクーポン情報を抽出します。
        
        Args:
            soup: BeautifulSoupオブジェクト
            
        Returns:
            クーポン情報のリスト
        """
        coupons = []
        
        # クーポンの各テーブルを取得
        coupon_tables = soup.select("div.usingPointToggle table.couponTbl")
        
        for table in coupon_tables:
            try:
                # クーポン名
                name_elem = table.select_one("p.couponMenuName")
                name = name_elem.text.strip() if name_elem else "不明なクーポン"
                
                # 価格
                price_elem = table.select_one("span.fs16.fgPink")
                price_text = price_elem.text.strip() if price_elem else ""
                # 数字以外の文字を削除して整数に変換
                price = int(re.sub(r'[^\d]', '', price_text)) if re.search(r'\d', price_text) else 0
                
                # 説明文
                description_elem = table.select_one("p.fgGray.fs11.wbba")
                description = description_elem.text.strip() if description_elem else ""
                
                # カテゴリー（メニューアイコン）
                categories = []
                category_elems = table.select("ul.couponMenuIcons li.couponMenuIcon")
                for elem in category_elems:
                    categories.append(elem.text.strip())
                
                # 条件
                conditions = {}
                
                # 来店日条件
                visit_date_dt = table.select_one("dt.mT5.fl.fgPink:-soup-contains('来店日条件')")
                if visit_date_dt:
                    visit_date_dd = visit_date_dt.find_next("dd")
                    if visit_date_dd:
                        conditions["来店日条件"] = visit_date_dd.text.strip()
                
                # 対象スタイリスト
                stylist_dt = table.select_one("dt.mT5.fl.fgPink:-soup-contains('対象スタイリスト')")
                if stylist_dt:
                    stylist_dd = stylist_dt.find_next("dd")
                    if stylist_dd:
                        conditions["対象スタイリスト"] = stylist_dd.text.strip()
                
                # その他条件
                other_dt = table.select_one("dt.mT5.fl.fgPink:-soup-contains('その他条件')")
                if other_dt:
                    other_dd = other_dt.find_next("dd")
                    if other_dd:
                        conditions["その他条件"] = other_dd.text.strip()
                
                # クーポン情報を作成
                coupon = CouponInfo(
                    name=name,
                    price=price,
                    description=description,
                    categories=categories,
                    conditions=conditions
                )
                
                coupons.append(coupon)
                
            except Exception as e:
                self.logger.error(f"クーポン情報の抽出エラー: {str(e)}")
                continue
        
        return coupons

    async def get_all_stylists(self, salon_url: str) -> List[StylistInfo]:
        """
        サロンの全スタイリスト情報を取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            全スタイリスト情報のリスト
        """
        self.logger.info(f"サロンの全スタイリスト情報を取得中: {salon_url}")
        
        # スタイリスト情報の取得
        stylist_info_list = await self.get_stylist_links(salon_url)
        
        # スタイリスト情報の作成
        stylist_info_tasks = [self.get_stylist_info(stylist_info) for stylist_info in stylist_info_list]
        stylist_infos = await asyncio.gather(*stylist_info_tasks, return_exceptions=True)
        
        # エラーをフィルタリング
        all_stylists = []
        for stylist_info in stylist_infos:
            if isinstance(stylist_info, Exception):
                self.logger.error(f"スタイリスト情報取得エラー: {str(stylist_info)}")
            else:
                all_stylists.append(stylist_info)
        
        self.logger.info(f"{len(all_stylists)}人のスタイリスト情報を取得しました")
        return all_stylists
        
    # 便利なヘルパーメソッド
    async def fetch_all_data(self, salon_url: str) -> Tuple[List[StylistInfo], List[CouponInfo]]:
        """
        サロンの全データ（スタイリスト情報とクーポン情報）を取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            (スタイリスト情報リスト, クーポン情報リスト)のタプル
        """
        # URLの検証
        if not await self.validate_url(salon_url):
            raise ValidationError(f"無効なサロンURL: {salon_url}")
            
        # 並列でスタイリストとクーポンを取得
        stylists_task = self.get_all_stylists(salon_url)
        coupons_task = self.get_coupons(salon_url)
        
        stylists, coupons = await asyncio.gather(stylists_task, coupons_task)
        
        return stylists, coupons
