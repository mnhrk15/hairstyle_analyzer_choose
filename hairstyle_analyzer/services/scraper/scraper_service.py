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

    async def get_stylist_links(self, salon_url: str) -> List[str]:
        """
        サロンページからスタイリストへのリンクを取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            スタイリストページへのURLリスト
            
        Raises:
            NetworkError: ネットワーク関連のエラーが発生した場合
            ParseError: HTML解析中にエラーが発生した場合
        """
        self.logger.info(f"サロンページからスタイリストリンクを取得中: {salon_url}")
        
        # URLの検証
        if not await self.validate_url(salon_url):
            raise ValidationError(f"無効なサロンURL: {salon_url}")
        
        # ページの取得（レート制限・キャッシュ機能付き）
        stylist_page_url = salon_url + "stylist/"
        page_content = await self._rate_limited_request(stylist_page_url)
        soup = self._parse_html(page_content)
        
        # スタイリストリンクの検索
        stylist_links = []
        try:
            links = soup.select(self.config.stylist_link_selector)
            base_url = salon_url.rstrip('/')
            
            for link in links:
                href = link.get('href')
                if href:
                    full_url = urljoin(base_url, href)
                    stylist_links.append(full_url)
            
            self.logger.info(f"{len(stylist_links)}人のスタイリストリンクを取得しました")
            return stylist_links
        except Exception as e:
            raise ParseError(f"スタイリストリンク取得エラー: {str(e)}", {
                "url": salon_url,
                "selector": self.config.stylist_link_selector
            })

    async def get_stylist_info(self, stylist_url: str) -> StylistInfo:
        """
        スタイリストページから詳細情報を取得します。
        
        Args:
            stylist_url: スタイリストページのURL
            
        Returns:
            スタイリスト情報
            
        Raises:
            NetworkError: ネットワーク関連のエラーが発生した場合
            ParseError: HTML解析中にエラーが発生した場合
        """
        self.logger.info(f"スタイリスト情報を取得中: {stylist_url}")
        
        # ページの取得（レート制限・キャッシュ機能付き）
        page_content = await self._rate_limited_request(stylist_url)
        soup = self._parse_html(page_content)
        
        try:
            # スタイリスト名の取得
            name_element = soup.select_one(self.config.stylist_name_selector)
            name = name_element.text.strip() if name_element else "名前不明"
            
            # スタイリスト説明の取得
            desc_element = soup.select_one(self.config.stylist_description_selector)
            description = desc_element.text.strip() if desc_element else ""
            
            # 役職の取得（存在する場合）
            position = None
            position_element = soup.find('p', class_='fs12')
            if position_element:
                position = position_element.text.strip()
            
            stylist_info = StylistInfo(
                name=name,
                description=description,
                position=position
            )
            
            self.logger.info(f"スタイリスト情報を取得しました: {name}")
            return stylist_info
        except Exception as e:
            raise ParseError(f"スタイリスト情報取得エラー: {str(e)}", {
                "url": stylist_url
            })

    async def get_coupons(self, salon_url: str) -> List[CouponInfo]:
        """
        サロンページからクーポン情報を取得します。
        複数ページにわたるクーポン情報も取得します。
        
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
        
        # クーポンページのURL作成
        coupon_url = salon_url.rstrip('/') + "/coupon/"
        
        # 1ページ目の取得
        coupons = await self._get_coupons_from_page(coupon_url)
        all_coupons = coupons.copy()
        
        # 2ページ目以降の取得（設定された上限まで）
        page_tasks = []
        for page_num in range(self.config.coupon_page_start_number, self.config.coupon_page_limit + 1):
            # ページパラメータを追加したURL
            next_page_url = self._add_page_param(coupon_url, page_num)
            page_tasks.append(self._get_coupons_from_page(next_page_url))
        
        # 並列処理で複数ページを取得
        if page_tasks:
            results = await asyncio.gather(*page_tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    self.logger.warning(f"クーポンページ取得エラー: {str(result)}")
                    continue
                    
                if result:  # 結果がある場合のみ追加
                    all_coupons.extend(result)
        
        self.logger.info(f"{len(all_coupons)}件のクーポン情報を取得しました")
        return all_coupons

    async def _get_coupons_from_page(self, page_url: str) -> List[CouponInfo]:
        """
        クーポンページから1ページ分のクーポン情報を取得します。
        
        Args:
            page_url: クーポンページのURL
            
        Returns:
            クーポン情報のリスト
        """
        try:
            # ページの取得（レート制限・キャッシュ機能付き）
            page_content = await self._rate_limited_request(page_url)
            soup = self._parse_html(page_content)
            
            coupons = []
            # クーポン要素の検索
            coupon_elements = soup.find_all(class_=self.config.coupon_class_name)
            
            for element in coupon_elements:
                name = element.text.strip()
                
                # 価格情報の取得（存在する場合）
                price = None
                price_element = element.find_next(class_='price')
                if price_element:
                    price = price_element.text.strip()
                
                coupons.append(CouponInfo(
                    name=name,
                    price=price
                ))
            
            return coupons
        except Exception as e:
            raise ParseError(f"クーポン情報取得エラー: {str(e)}", {
                "url": page_url,
                "class_name": self.config.coupon_class_name
            })

    def _add_page_param(self, url: str, page_number: int) -> str:
        """
        URLにページ番号パラメータを追加します。
        
        Args:
            url: 元のURL
            page_number: ページ番号
            
        Returns:
            ページ番号パラメータが追加されたURL
        """
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        # ページパラメータを追加/更新
        query_params[self.config.coupon_page_parameter_name] = [str(page_number)]
        
        # URLを再構築
        new_query = urlencode(query_params, doseq=True)
        new_parts = list(parsed_url)
        new_parts[4] = new_query
        
        return urlunparse(new_parts)

    async def get_all_stylists(self, salon_url: str) -> List[StylistInfo]:
        """
        サロンの全スタイリスト情報を取得します。
        
        Args:
            salon_url: サロンページのURL
            
        Returns:
            全スタイリスト情報のリスト
        """
        self.logger.info(f"サロンの全スタイリスト情報を取得中: {salon_url}")
        
        # スタイリストリンクの取得
        stylist_links = await self.get_stylist_links(salon_url)
        
        # 並列処理でスタイリスト情報を取得（コルーチンの数を制限）
        chunk_size = 5  # 一度に処理するスタイリスト数
        all_stylists = []
        
        for i in range(0, len(stylist_links), chunk_size):
            chunk = stylist_links[i:i+chunk_size]
            tasks = [self.get_stylist_info(link) for link in chunk]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # エラーをフィルタリング
            for j, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"スタイリスト情報取得エラー: {chunk[j]} - {str(result)}")
                else:
                    all_stylists.append(result)
                    
            # 次のチャンクの前に少し待機
            if i + chunk_size < len(stylist_links):
                await asyncio.sleep(1)
        
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
