"""
ScraperServiceのテストモジュール

このモジュールでは、ScraperServiceクラスの機能をテストします。
"""

import asyncio
import json
import pytest
import httpx
from pathlib import Path
from bs4 import BeautifulSoup
from unittest.mock import patch, MagicMock, AsyncMock

from hairstyle_analyzer.services.scraper import ScraperService
from hairstyle_analyzer.services.scraper.scraper_service import (
    NetworkError, ParseError, ValidationError
)
from hairstyle_analyzer.config.models import ScraperConfig


@pytest.fixture
def scraper_config():
    """ScraperConfigのテストフィクスチャ"""
    return ScraperConfig(
        base_url="https://beauty.hotpepper.jp/slnH000000000/",
        stylist_link_selector="p.mT10.fs16.b > a[href*='/stylist/T']",
        stylist_name_selector=".fs16.b",
        stylist_description_selector=".fgPink",
        coupon_class_name="couponMenuName",
        coupon_page_parameter_name="PN",
        coupon_page_start_number=2,
        coupon_page_limit=3,
        timeout=10,
        max_retries=3,
        retry_delay=1
    )


@pytest.fixture
def test_cache_path(tmp_path):
    """一時キャッシュパスのテストフィクスチャ"""
    return tmp_path / "test_cache.json"


@pytest.fixture
async def scraper_service(scraper_config, test_cache_path):
    """ScraperServiceのテストフィクスチャ"""
    service = ScraperService(scraper_config, test_cache_path)
    await service.initialize()
    yield service
    await service.close()


def create_mock_html(content_type="stylist_list"):
    """テスト用のHTMLを生成する"""
    if content_type == "stylist_list":
        return """
        <html>
            <body>
                <p class="mT10 fs16 b">
                    <a href="/slnH000000000/stylist/T000000001/">スタイリスト1</a>
                </p>
                <p class="mT10 fs16 b">
                    <a href="/slnH000000000/stylist/T000000002/">スタイリスト2</a>
                </p>
            </body>
        </html>
        """
    elif content_type == "stylist_detail":
        return """
        <html>
            <body>
                <p class="fs16 b">スタイリスト名</p>
                <p class="fgPink">スタイリスト説明文</p>
                <p class="fs12">役職名</p>
            </body>
        </html>
        """
    elif content_type == "coupon_list":
        return """
        <html>
            <body>
                <div class="couponMenuName">クーポン1</div>
                <div class="price">1000円</div>
                <div class="couponMenuName">クーポン2</div>
                <div class="price">2000円</div>
            </body>
        </html>
        """
    else:
        return "<html><body></body></html>"


class MockResponse:
    """HTTPレスポンスのモック"""
    def __init__(self, text, status_code=200, headers=None):
        self.status_code = status_code
        self._text = text
        self.headers = headers or {}
        
    @property
    def text(self):
        return self._text
        
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("HTTP Error", request=None, response=self)


class TestScraperService:
    """ScraperServiceのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_validate_url_valid(self, scraper_service):
        """有効なURLの検証テスト"""
        valid_url = "https://beauty.hotpepper.jp/slnH000000000/"
        is_valid = await scraper_service.validate_url(valid_url)
        assert is_valid is True
        
    @pytest.mark.asyncio
    async def test_validate_url_invalid(self, scraper_service):
        """無効なURLの検証テスト"""
        invalid_urls = [
            "https://example.com/",
            "https://beauty.hotpepper.jp/incorrect/",
            "invalid_url"
        ]
        for url in invalid_urls:
            is_valid = await scraper_service.validate_url(url)
            assert is_valid is False
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_page(self, mock_get, scraper_service):
        """ページ取得のテスト"""
        mock_html = create_mock_html()
        mock_get.return_value = MockResponse(mock_html)
        
        content = await scraper_service._fetch_page("https://beauty.hotpepper.jp/slnH000000000/")
        assert content == mock_html
        mock_get.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_page_network_error(self, mock_get, scraper_service):
        """ネットワークエラーのテスト"""
        mock_get.side_effect = httpx.RequestError("Connection error")
        
        with pytest.raises(NetworkError):
            await scraper_service._fetch_page("https://beauty.hotpepper.jp/slnH000000000/")
            
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_rate_limited_request_cache(self, mock_get, scraper_service):
        """レート制限とキャッシュのテスト"""
        url = "https://beauty.hotpepper.jp/slnH000000000/"
        mock_html = create_mock_html()
        
        # 最初のリクエスト
        mock_get.return_value = MockResponse(mock_html)
        content1 = await scraper_service._rate_limited_request(url)
        assert content1 == mock_html
        assert mock_get.call_count == 1
        
        # 2回目のリクエスト（キャッシュから取得されるはず）
        content2 = await scraper_service._rate_limited_request(url)
        assert content2 == mock_html
        assert mock_get.call_count == 1  # 呼び出し回数が増えないことを確認
        
    @pytest.mark.asyncio
    @patch.object(ScraperService, '_rate_limited_request')
    async def test_get_stylist_links(self, mock_request, scraper_service):
        """スタイリストリンク取得のテスト"""
        mock_html = create_mock_html("stylist_list")
        mock_request.return_value = mock_html
        
        links = await scraper_service.get_stylist_links("https://beauty.hotpepper.jp/slnH000000000/")
        assert len(links) == 2
        assert "T000000001" in links[0]
        assert "T000000002" in links[1]
        
    @pytest.mark.asyncio
    @patch.object(ScraperService, '_rate_limited_request')
    async def test_get_stylist_info(self, mock_request, scraper_service):
        """スタイリスト情報取得のテスト"""
        mock_html = create_mock_html("stylist_detail")
        mock_request.return_value = mock_html
        
        info = await scraper_service.get_stylist_info("https://beauty.hotpepper.jp/slnH000000000/stylist/T000000001/")
        assert info.name == "スタイリスト名"
        assert info.description == "スタイリスト説明文"
        assert info.position == "役職名"
        
    @pytest.mark.asyncio
    @patch.object(ScraperService, '_rate_limited_request')
    async def test_get_coupons_from_page(self, mock_request, scraper_service):
        """クーポン情報取得のテスト"""
        mock_html = create_mock_html("coupon_list")
        mock_request.return_value = mock_html
        
        coupons = await scraper_service._get_coupons_from_page("https://beauty.hotpepper.jp/slnH000000000/coupon/")
        assert len(coupons) == 2
        assert coupons[0].name == "クーポン1"
        assert coupons[0].price == "1000円"
        assert coupons[1].name == "クーポン2"
        assert coupons[1].price == "2000円"
        
    @pytest.mark.asyncio
    @patch.object(ScraperService, 'get_stylist_links')
    @patch.object(ScraperService, 'get_stylist_info')
    async def test_get_all_stylists(self, mock_get_info, mock_get_links, scraper_service):
        """全スタイリスト情報取得のテスト"""
        # スタイリストリンクのモック
        mock_get_links.return_value = [
            "https://beauty.hotpepper.jp/slnH000000000/stylist/T000000001/",
            "https://beauty.hotpepper.jp/slnH000000000/stylist/T000000002/"
        ]
        
        # スタイリスト情報のモック
        from hairstyle_analyzer.data.models import StylistInfo
        mock_get_info.side_effect = [
            StylistInfo(name="スタイリスト1", description="説明1", position="役職1"),
            StylistInfo(name="スタイリスト2", description="説明2", position="役職2")
        ]
        
        stylists = await scraper_service.get_all_stylists("https://beauty.hotpepper.jp/slnH000000000/")
        assert len(stylists) == 2
        assert stylists[0].name == "スタイリスト1"
        assert stylists[1].name == "スタイリスト2"
        
    @pytest.mark.asyncio
    @patch.object(ScraperService, 'get_all_stylists')
    @patch.object(ScraperService, 'get_coupons')
    async def test_fetch_all_data(self, mock_get_coupons, mock_get_stylists, scraper_service):
        """全データ取得のテスト"""
        # スタイリスト情報のモック
        from hairstyle_analyzer.data.models import StylistInfo, CouponInfo
        mock_stylists = [
            StylistInfo(name="スタイリスト1", description="説明1", position="役職1"),
            StylistInfo(name="スタイリスト2", description="説明2", position="役職2")
        ]
        mock_get_stylists.return_value = mock_stylists
        
        # クーポン情報のモック
        mock_coupons = [
            CouponInfo(name="クーポン1", price="1000円"),
            CouponInfo(name="クーポン2", price="2000円")
        ]
        mock_get_coupons.return_value = mock_coupons
        
        stylists, coupons = await scraper_service.fetch_all_data("https://beauty.hotpepper.jp/slnH000000000/")
        assert len(stylists) == 2
        assert len(coupons) == 2
        assert stylists[0].name == "スタイリスト1"
        assert coupons[0].name == "クーポン1"
