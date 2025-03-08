# ヘアスタイル画像解析システム 技術ドキュメント

## 1. システム概要

ヘアスタイル画像解析システムは、ヘアスタイルの画像を分析し、最適なスタイリスト、クーポン、スタイルタイトルを自動的に提案するアプリケーションです。Google Gemini APIを活用した画像解析と、ホットペッパービューティーからのデータ取得を組み合わせることで、効率的なマッチングを実現します。

### 1.1 主要機能

- **画像分析**: ヘアスタイル画像の特徴（カテゴリ、髪色、カット技法、スタイリング方法、印象）を抽出
- **属性分析**: 性別と髪の長さの判定
- **テンプレートマッチング**: 分析結果に基づいて最適なスタイルタイトルとメニュー提案
- **スタイリスト選択**: 髪型に最適なスタイリストを推薦
- **クーポン選択**: 髪型に適したクーポンを推薦
- **Excel出力**: 結果の一括出力
- **Webインターフェース**: Streamlitを使用したユーザーフレンドリーなUI

### 1.2 技術スタック

- **言語**: Python 3.9+
- **AI/ML**: Google Gemini API (画像分析、自然言語処理)
- **UI**: Streamlit
- **データ処理**: Pandas, Pydantic
- **Web スクレイピング**: BeautifulSoup, HTTPX
- **ファイル出力**: OpenPyXL (Excel)
- **その他**: asyncio（非同期処理）、logging（ログ機能）

## 2. システムアーキテクチャ

### 2.1 全体構成

システムは以下の主要コンポーネントで構成されています：

```
hairstyle_analyzer/
├── core/                 # コアビジネスロジック
│   ├── image_analyzer.py # 画像分析
│   ├── template_matcher.py # テンプレートマッチング
│   ├── style_matching.py # スタイリスト・クーポンマッチング
│   ├── excel_exporter.py # Excel出力
│   └── processor.py      # メイン処理フロー
├── data/                 # データモデルと管理
│   ├── models.py         # Pydanticモデル
│   ├── interfaces.py     # インターフェース定義
│   ├── config_manager.py # 設定管理
│   ├── template_manager.py # テンプレート管理
│   └── cache_manager.py  # キャッシュ管理
├── services/             # 外部サービス連携
│   ├── gemini/           # Gemini API連携
│   └── scraper/          # Webスクレイピング
├── ui/                   # ユーザーインターフェース
│   ├── streamlit_app.py  # メインアプリ
│   └── components/       # UIコンポーネント
└── utils/                # ユーティリティ
    ├── errors.py         # エラー定義
    ├── image_utils.py    # 画像処理
    ├── logging_utils.py  # ロギング
    └── system_utils.py   # システムリソース管理
```

### 2.2 データフロー

1. ユーザーが画像をアップロード
2. Gemini APIによる画像分析（スタイルと属性）
3. テンプレートデータベースとのマッチング
4. ホットペッパービューティーからのスタイリスト・クーポン情報取得
5. 画像分析結果とスタイリスト・クーポン情報のマッチング
6. 結果の表示とExcel出力

## 3. コアモジュール詳細

### 3.1 画像分析（ImageAnalyzer）

`ImageAnalyzer`クラスは、Gemini APIを使用して画像分析を行います。

#### 主要機能

- **画像分析**: カテゴリ、特徴（髪色、カット技法、スタイリング、印象）、キーワードの抽出
- **属性分析**: 性別（レディース/メンズ）と髪の長さの判定
- **キャッシュ機能**: 分析結果のキャッシュによるAPI呼び出し最適化

#### 重要メソッド

```python
async def analyze_image(self, image_path: Path, categories: List[str], use_cache: Optional[bool] = None) -> Optional[StyleAnalysisProtocol]:
    """画像を分析し、スタイル情報を抽出"""

async def analyze_attributes(self, image_path: Path, use_cache: Optional[bool] = None) -> Optional[AttributeAnalysisProtocol]:
    """画像から性別と髪の長さを分析"""

async def analyze_full(self, image_path: Path, categories: List[str], use_cache: Optional[bool] = None) -> Tuple[Optional[StyleAnalysisProtocol], Optional[AttributeAnalysisProtocol]]:
    """スタイル分析と属性分析を同時に実行"""
```

### 3.2 テンプレートマッチング（TemplateMatcher）

`TemplateMatcher`クラスは、分析結果に基づいて最適なテンプレートを選択します。

#### 主要機能

- **テンプレート検索**: 分析結果に最適なスタイルタイトル、メニュー、コメントの提案
- **AIマッチング**: Gemini APIを使った高度なテンプレート選択（オプション）
- **スコアリング**: カテゴリ一致、キーワード類似度、テキスト内容の評価に基づく選択

#### 重要メソッド

```python
def find_best_template(self, analysis: StyleAnalysisProtocol) -> Optional[Template]:
    """分析結果に最適なテンプレートを検索"""

async def find_best_template_with_ai(self, image_path: Path, gemini_service: GeminiService, analysis: Optional[StyleAnalysisProtocol] = None, use_category_filter: bool = True, max_templates: int = 50) -> Tuple[Optional[Template], Optional[str], bool]:
    """AIを使った高度なテンプレート選択"""
```

### 3.3 スタイルマッチング（StyleMatchingService）

`StyleMatchingService`クラスは、画像分析結果に基づいて最適なスタイリストとクーポンを選択します。

#### 主要機能

- **スタイリスト選択**: 画像分析結果に基づく最適なスタイリストの選択
- **クーポン選択**: 画像分析結果に基づく最適なクーポンの選択
- **テキスト類似度計算**: スタイリスト説明文とクーポン内容の分析による類似度スコアリング

#### 重要メソッド

```python
async def select_stylist(self, image_path: Path, stylists: List[StylistInfoProtocol], analysis: StyleAnalysisProtocol) -> Tuple[Optional[StylistInfoProtocol], Optional[str]]:
    """画像と分析結果に基づいて最適なスタイリストを選択"""

async def select_coupon(self, image_path: Path, coupons: List[CouponInfoProtocol], analysis: StyleAnalysisProtocol) -> Tuple[Optional[CouponInfoProtocol], Optional[str]]:
    """画像と分析結果に基づいて最適なクーポンを選択"""
```

### 3.4 Excel出力（ExcelExporter）

`ExcelExporter`クラスは、処理結果をExcel形式で出力します。

#### 主要機能

- **Excel生成**: 処理結果のExcelファイル出力
- **カスタムヘッダー**: 設定ファイルによるカスタマイズ可能なヘッダー
- **スタイル適用**: セル書式の自動調整

#### 重要メソッド

```python
def export(self, results: List[ProcessResultProtocol], output_path: Path) -> Path:
    """処理結果をExcel形式で出力"""

def get_binary_data(self, results: List[ProcessResultProtocol]) -> bytes:
    """処理結果のExcelバイナリデータを取得"""
```

### 3.5 メイン処理フロー（MainProcessor）

`MainProcessor`クラスは、アプリケーションの中心となる処理フローを制御します。

#### 主要機能

- **画像処理**: 単一および複数画像の処理フロー管理
- **バッチ処理**: システムリソースを考慮した最適なバッチサイズ計算とバッチ処理
- **進捗管理**: 処理進捗の追跡と通知

#### 重要メソッド

```python
async def process_single_image(self, image_path: Path, stylists=None, coupons=None, use_cache: Optional[bool] = None) -> Optional[ProcessResultProtocol]:
    """単一の画像を処理"""

async def process_images(self, image_paths: List[Path], use_cache: Optional[bool] = None) -> List[ProcessResultProtocol]:
    """複数の画像を処理"""

async def process_images_with_external_data(self, image_paths: List[Path], stylists: List[StylistInfoProtocol], coupons: List[CouponInfoProtocol], use_cache: Optional[bool] = None) -> List[ProcessResultProtocol]:
    """外部データを使用して複数の画像を処理"""
```

## 4. サービス連携

### 4.1 Gemini API連携（GeminiService）

`GeminiService`クラスは、Google Gemini APIと連携して画像分析を行います。

#### 主要機能

- **APIリクエスト管理**: リクエスト形成、送信、レスポンス処理
- **エラーハンドリング**: エラーの検出、リトライ、フォールバックモデル切替
- **プロンプト管理**: 分析・選択用のプロンプトテンプレート管理

#### 重要メソッド

```python
async def _call_gemini_api(self, prompt: str, image_path: Optional[Path] = None, use_fallback: bool = False, attempt: int = 1) -> str:
    """Gemini APIを呼び出し"""

def _parse_json_response(self, response_text: str) -> Dict[str, Any]:
    """APIレスポンスからJSONデータを抽出・パース"""
```

### 4.2 Webスクレイピング（ScraperService）

`ScraperService`クラスは、ホットペッパービューティーからデータをスクレイピングします。

#### 主要機能

- **スタイリスト情報取得**: サロンページからスタイリスト情報を抽出
- **クーポン情報取得**: サロンページからクーポン情報を抽出
- **ページネーション処理**: 複数ページにわたるデータの取得
- **レート制限対応**: リクエスト間隔の制御とキャッシュ機能

#### 重要メソッド

```python
async def get_all_stylists(self, salon_url: str) -> List[StylistInfo]:
    """サロンの全スタイリスト情報を取得"""

async def get_coupons(self, salon_url: str) -> List[CouponInfo]:
    """サロンページからクーポン情報を取得"""

async def fetch_all_data(self, salon_url: str) -> Tuple[List[StylistInfo], List[CouponInfo]]:
    """サロンの全データ（スタイリスト情報とクーポン情報）を取得"""
```

## 5. データ管理

### 5.1 設定管理（ConfigManager）

`ConfigManager`クラスは、アプリケーションの設定を管理します。

#### 主要機能

- **YAML設定読み込み**: 設定ファイルの読み込みと検証
- **環境変数統合**: .env ファイルと環境変数からの設定取得
- **設定変更管理**: 設定のバックアップと更新

#### 重要メソッド

```python
def validate(self) -> None:
    """設定値を検証"""

def update_config(self, new_config: Dict[str, Any]) -> None:
    """設定辞書を更新"""

def save_api_key(self, api_key: str) -> None:
    """Gemini APIキーを.envファイルに保存"""
```

### 5.2 テンプレート管理（TemplateManager）

`TemplateManager`クラスは、スタイルテンプレートを管理します。

#### 主要機能

- **CSV読み込み**: テンプレートCSVファイルの読み込み
- **カテゴリ管理**: カテゴリ別テンプレートの整理
- **テンプレート検索**: 最適なテンプレートの検索機能

#### 重要メソッド

```python
def get_templates_by_category(self, category: str) -> List[Template]:
    """指定されたカテゴリのテンプレートリストを取得"""

def find_best_template(self, analysis: StyleAnalysisProtocol) -> Optional[Template]:
    """分析結果に最も合うテンプレートを検索"""
```

### 5.3 キャッシュ管理（CacheManager）

`CacheManager`クラスは、処理結果のキャッシュを管理します。

#### 主要機能

- **キャッシュ保存**: 処理結果の保存と読み込み
- **TTL管理**: 有効期限に基づくキャッシュ管理
- **サイズ制限**: キャッシュサイズの制限機能

#### 重要メソッド

```python
def get(self, key: str, context: str = "") -> Optional[Any]:
    """指定されたキーのキャッシュデータを取得"""

def set(self, key: str, value: Any, ttl: Optional[float] = None, context: str = "") -> None:
    """キャッシュにデータを設定"""

def clear(self, pattern: Optional[str] = None) -> int:
    """キャッシュをクリア"""
```

## 6. ユーティリティ

### 6.1 エラー処理（errors.py）

エラー処理システムは、アプリケーション全体で一貫したエラーハンドリングを提供します。

#### 主要機能

- **カスタム例外階層**: 専用例外クラス定義
- **エラーハンドリングデコレータ**: 関数のエラーハンドリング自動化
- **エラーメッセージ生成**: ユーザーフレンドリーなエラーメッセージ

#### 重要コンポーネント

```python
class AppError(Exception):
    """アプリケーション基本エラークラス"""

def with_error_handling(error_type: Type[AppError] = AppError, error_message: str = "処理中にエラーが発生しました", logger: Optional[logging.Logger] = None, raise_original: bool = False, return_on_error: Optional[Any] = None, log_level: int = logging.ERROR) -> Callable:
    """エラーハンドリングを行うデコレータ"""

def format_error_message(error: Exception) -> str:
    """例外からユーザーフレンドリーなエラーメッセージを生成"""
```

### 6.2 画像処理ユーティリティ（image_utils.py）

画像処理ユーティリティは、画像ファイルの処理と検証機能を提供します。

#### 主要機能

- **画像検証**: ファイル形式とサイズの検証
- **画像エンコード**: Base64エンコーディング
- **画像リサイズ**: アスペクト比を維持したリサイズ

#### 重要関数

```python
def is_valid_image(file_path: Union[str, Path]) -> bool:
    """与えられたファイルが有効な画像かどうかを判定"""

def encode_image(file_path: Union[str, Path]) -> str:
    """画像をBase64でエンコード"""

def resize_image(file_path: Union[str, Path], max_size: int = 1024, output_path: Optional[Union[str, Path]] = None) -> Path:
    """画像をリサイズ"""
```

### 6.3 ロギングユーティリティ（logging_utils.py）

ロギングユーティリティは、アプリケーション全体で一貫したログ記録を提供します。

#### 主要機能

- **ロガー設定**: ファイルおよびコンソール出力設定
- **コンテキスト情報**: 呼び出し元情報の自動付加
- **実行時間測定**: 関数実行時間の自動記録
- **進捗ロギング**: 長時間処理の進捗表示

#### 重要コンポーネント

```python
class ContextFilter(logging.Filter):
    """コンテキスト情報を追加するログフィルター"""

def setup_logger(name: str = None, level: int = logging.INFO, log_file: Optional[Union[str, Path]] = None, console: bool = True, format_str: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s") -> logging.Logger:
    """ロガーをセットアップ"""

def log_execution_time(logger: Optional[logging.Logger] = None, level: int = logging.DEBUG) -> Callable:
    """関数の実行時間をログに記録するデコレータ"""

class ProgressLogger:
    """進捗状況をログに記録するクラス"""
```

### 6.4 システムユーティリティ（system_utils.py）

システムユーティリティは、システムリソースの監視と最適化を行います。

#### 主要機能

- **リソース監視**: メモリ使用量、CPU使用率の監視
- **バッチサイズ計算**: システムリソースに基づく最適なバッチサイズ計算
- **ディレクトリ操作**: ファイルシステム操作の安全な実行

#### 重要関数

```python
def calculate_optimal_batch_size(memory_per_item_mb: int = 5, max_memory_percent: float = 70.0, min_batch_size: int = 1, max_batch_size: int = 20, cpu_factor: float = 0.5) -> int:
    """システムリソースに基づいて最適なバッチサイズを計算"""

def get_memory_usage() -> Dict[str, Any]:
    """メモリ使用状況を取得"""

def get_cpu_usage() -> Dict[str, Any]:
    """CPU使用状況を取得"""
```

## 7. UI コンポーネント

### 7.1 メインアプリ（streamlit_app.py）

Streamlitアプリケーションのメインエントリーポイントです。

#### 主要機能

- **画像アップロード**: 画像のアップロードとプレビュー
- **処理実行**: 画像処理の実行と進捗表示
- **結果表示**: 処理結果の表示とExcelダウンロード
- **設定管理**: サイドバーでの設定変更

### 7.2 UIコンポーネント

UIは複数の再利用可能なコンポーネントで構成されています。

#### 主要コンポーネント

- **ファイルアップローダー**: 画像ファイルのアップロードとプレビュー
- **プログレスバー**: 処理進捗の視覚化
- **結果表示**: 処理結果のテーブル表示と詳細表示
- **設定パネル**: 設定の表示と編集
- **画像プレビュー**: 画像のグリッド表示とギャラリービュー
- **エラー表示**: ユーザーフレンドリーなエラーメッセージの表示

## 8. 設定とカスタマイズ

### 8.1 設定ファイル（config.yaml）

アプリケーションの設定はYAMLファイルで管理されています。主な設定項目は以下の通りです：

```yaml
# キャッシュ設定
cache:
  ttl_days: 30          # キャッシュ有効期限（日数）
  max_size: 10000       # 最大キャッシュエントリ数

# Gemini API設定
gemini:
  model: "gemini-2.0-flash"  # 使用するGeminiモデル
  fallback_model: "gemini-2.0-flash-lite"  # フォールバックモデル
  max_tokens: 300       # 生成する最大トークン数
  temperature: 0.7      # 生成の温度パラメータ
  # プロンプトテンプレート
  prompt_template: |
    ...

# スクレイパー設定
scraper:
  base_url: ""  # スクレイピング対象のベースURL
  stylist_link_selector: "..."  # スタイリストリンクのセレクタ
  ...

# Excel出力設定
excel:
  headers:  # Excel出力のヘッダー定義
    A: "スタイリスト名"
    B: "クーポン名"
    ...

# 処理設定
processing:
  batch_size: 5  # バッチサイズ
  api_delay: 1.0  # API呼び出し間の遅延（秒）
  max_retries: 3  # 最大リトライ回数
  ...

# パス設定
paths:
  image_folder: "./assets/samples"  # 画像フォルダのパス
  template_csv: "./assets/templates/template.csv"  # テンプレートCSVファイルのパス
  ...

# ロギング設定
logging:
  log_file: "./logs/app.log"  # ログファイルのパス
  log_level: "INFO"  # ログレベル
```

### 8.2 環境変数（.env）

機密情報や環境固有の設定は.envファイルで管理されます：

```
# Google Gemini API Key
GEMINI_API_KEY=your_api_key_here

# ホットペッパービューティーのURL（スクレイピング対象）
HOTPEPPER_URL=https://beauty.hotpepper.jp/slnH000000000/

# その他の設定
# DEBUG=True
```

### 8.3 テンプレートCSV

スタイルテンプレートはCSVファイルで管理されます。フォーマットは以下の通りです：

| category | title | menu | comment | hashtag |
|----------|-------|------|---------|---------|
| 最新トレンド | ゆるふわショートボブ | カット+カラー | 柔らかい質感と動きが特徴のショートボブ。顔周りを優しく包み込むスタイルです。 | ショートボブ,ゆるふわ,柔らかい質感,透明感,小顔効果 |

## 9. システム要件と設定

### 9.1 システム要件

- **Python**: 3.9以上
- **メモリ**: 最小4GB推奨（画像処理量によって変動）
- **ディスク容量**: 最小100MB（キャッシュやログによって増加）
- **インターネット接続**: Gemini APIとホットペッパービューティーへのアクセスに必要

### 9.2 必要パッケージ

```
# UI
streamlit>=1.41.0

# データ処理
pandas>=2.0.0
numpy>=1.24.0
pydantic>=2.4.0

# 画像処理
pillow>=10.0.0

# API連携
google-generativeai>=0.6.0
python-dotenv>=1.0.0

# Webスクレイピング
requests>=2.31.0
lxml>=4.9.0

# Excel処理
openpyxl>=3.1.0

# ユーティリティ
tqdm>=4.65.0
pyyaml>=6.0.0
psutil>=5.9.0

# スクレイピング関連
httpx==0.27.0
beautifulsoup4==4.12.2
tenacity==8.2.3
```

### 9.3 初期設定手順

1. リポジトリのクローン
2. 仮想環境のセットアップと依存関係のインストール
3. .envファイルの作成とGemini APIキーの設定
4. 設定ファイル（config.yaml）の編集
5. テンプレートCSVの準備

## 10. デプロイとメンテナンス

### 10.1 起動方法

```bash
# 通常起動
streamlit run hairstyle_analyzer/ui/streamlit_app.py

# または専用スクリプトを使用
python run_app.py
```

### 10.2 ログと監視

- ログファイル: `./logs/app.log`（設定可能）
- ログレベル: INFO（デフォルト、設定可能）
- 監視項目: API呼び出し、エラー発生、処理時間

### 10.3 トラブルシューティング

1. **API連携エラー**:
   - APIキーの確認
   - インターネット接続の確認
   - レート制限の確認

2. **スクレイピングエラー**:
   - URLの確認
   - HTML構造の変更確認
   - セレクターの更新

3. **処理エラー**:
   - ログファイルの確認
   - 画像形式の確認
   - メモリ使用量の確認

## 11. 拡張と改善

### 11.1 機能拡張

1. **AIモデルの変更**: 設定ファイルでGeminiのモデルを変更可能
2. **新規テンプレート追加**: テンプレートCSVを編集して新しいスタイルを追加
3. **スクレイピングサイト拡張**: 他の美容サイトへの対応も可能

### 11.2 パフォーマンス最適化

1. **バッチサイズ調整**: システム性能に合わせたバッチサイズの最適化
2. **キャッシュ設定**: TTLとサイズ制限の調整
3. **API遅延調整**: リクエスト間隔の最適化

### 11.3 UI改善

1. **新規コンポーネント**: 必要に応じて新しいUIコンポーネントを追加
2. **表示カスタマイズ**: 結果表示のカスタマイズ
3. **インタラクション追加**: ユーザー体験向上のためのインタラクション改善

## 12. まとめ

ヘアスタイル画像解析システムは、AIとウェブスクレイピング技術を組み合わせ、美容サロンの業務効率化を実現するアプリケーションです。モジュール化された設計、堅牢なエラーハンドリング、柔軟な拡張性を備えており、様々な環境での利用に適しています。定期的なメンテナンスとアップデートにより、長期的な安定運用が可能です。