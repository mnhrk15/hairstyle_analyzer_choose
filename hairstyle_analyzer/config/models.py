"""
設定モデルを定義するモジュール

このモジュールでは、アプリケーションの設定に関連するデータモデルを
Pydanticを使用して定義しています。
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ScraperConfig(BaseModel):
    """
    スクレイパーの設定モデル
    
    ホットペッパービューティサイトのスクレイピングに関する設定を含みます。
    """
    base_url: str = Field(..., description="スクレイピング対象のベースURL")
    stylist_link_selector: str = Field(..., description="スタイリストリンクのセレクタ")
    stylist_name_selector: str = Field(..., description="スタイリスト名のセレクタ")
    stylist_description_selector: str = Field(..., description="スタイリスト説明のセレクタ")
    coupon_class_name: str = Field(..., description="クーポン名のクラス名")
    coupon_page_parameter_name: str = Field("PN", description="クーポンページパラメータ名")
    coupon_page_start_number: int = Field(2, description="クーポンページ開始番号")
    coupon_page_limit: int = Field(3, description="クーポンページ数上限")
    timeout: int = Field(10, description="リクエストタイムアウト（秒）")
    max_retries: int = Field(3, description="最大リトライ回数")
    retry_delay: int = Field(1, description="リトライ間隔（秒）")
    
    @validator('timeout', 'max_retries', 'retry_delay', 'coupon_page_start_number', 'coupon_page_limit')
    def validate_positive_number(cls, v, values, **kwargs):
        if v <= 0:
            field_name = kwargs['field'].name
            raise ValueError(f"{field_name}は正の数でなければなりません")
        return v
    
    @validator('base_url')
    def validate_url(cls, v):
        if not v.startswith('http'):
            raise ValueError("base_urlはhttpまたはhttpsで始まる必要があります")
        return v


class GeminiConfig(BaseModel):
    """
    Gemini APIの設定モデル
    
    Gemini APIの利用に関する設定を含みます。
    """
    model: str
    fallback_model: Optional[str] = None
    max_tokens: int = 300
    temperature: float = 0.7
    prompt_template: str
    attribute_prompt_template: Optional[str] = None
    stylist_prompt_template: Optional[str] = None
    coupon_prompt_template: Optional[str] = None
    length_choices: Optional[List[str]] = None


class CacheConfig(BaseModel):
    """
    キャッシュの設定モデル
    
    データキャッシュに関する設定を含みます。
    """
    ttl_days: int = 30
    max_size: int = 10000


class ExcelConfig(BaseModel):
    """
    Excel出力の設定モデル
    
    Excel出力に関する設定を含みます。
    """
    headers: Dict[str, str]


class ProcessingConfig(BaseModel):
    """
    処理に関する設定モデル
    
    バッチ処理などの設定を含みます。
    """
    batch_size: int = 5
    api_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 1.0
    memory_per_image_mb: int = 5


class PathConfig(BaseModel):
    """
    パスに関する設定モデル
    
    ファイルパスに関する設定を含みます。
    """
    image_folder: str
    template_csv: str
    output_excel: str
    cache_file: str
    log_file: str


class LoggingConfig(BaseModel):
    """
    ロギングに関する設定モデル
    
    ログに関する設定を含みます。
    """
    log_file: str
    log_level: str = "INFO"


class AppConfig(BaseModel):
    """
    アプリケーション全体の設定モデル
    
    アプリケーション全体の設定を含みます。
    """
    cache: CacheConfig
    gemini: GeminiConfig
    scraper: ScraperConfig
    excel: ExcelConfig
    processing: ProcessingConfig
    paths: PathConfig
    logging: LoggingConfig
