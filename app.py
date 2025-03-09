"""
ヘアスタイル画像解析システム - エントリーポイント

このファイルはStreamlit Cloudでのデプロイ用のエントリーポイントです。
より明確な命名のため、streamlit_app.pyからapp.pyに変更されました。
"""

import os
import sys
import tempfile
from pathlib import Path
import streamlit as st
import logging
from dotenv import load_dotenv

# ロギングの初期化
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S,%03d",
)
logger = logging.getLogger("root")
logger.info("ロギングを初期化しました")

# Streamlitページ設定（必ず最初のStreamlitコマンドとして実行）
st.set_page_config(
    page_title="Style Generator",
    page_icon="💇",
    layout="wide",
)

# プロジェクトルートをPythonパスに追加
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

# 環境変数の設定とStreamlit Secretsの安全なアクセス
def setup_environment():
    """環境変数を設定し、APIキーを安全に取得します"""
    # .envファイルを優先的に読み込む（ローカル環境用）
    env_path = root_dir / ".env"
    is_env_loaded = False
    
    if env_path.exists():
        load_dotenv(env_path)
        print(f".envファイルを読み込みました: {env_path.absolute()}")
        is_env_loaded = True
        
        # 環境変数が存在するか確認
        if not "GEMINI_API_KEY" in os.environ:
            print("注意: GEMINI_API_KEYが.envファイルで設定されていません。画像処理機能が正常に動作しない可能性があります。")
    
    # シークレットファイルの存在を先にチェック
    secrets_path = root_dir / ".streamlit" / "secrets.toml"
    home_secrets_path = Path.home() / ".streamlit" / "secrets.toml"
    has_secrets_file = secrets_path.exists() or home_secrets_path.exists()
    
    # シークレットアクセスのエラーを抑制
    is_streamlit_cloud = False
    try:
        if has_secrets_file:
            # secretsが利用可能かを安全に確認
            try:
                # secretsにアクセス
                if "GEMINI_API_KEY" in st.secrets:
                    os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
                    is_streamlit_cloud = True
                
                if "HOTPEPPER_URL" in st.secrets:
                    os.environ["HOTPEPPER_URL"] = st.secrets["HOTPEPPER_URL"]
                    
                if is_streamlit_cloud:
                    logger.info("Streamlit Secretsからのキー取得: 成功")
                    print("Streamlit Secretsから環境変数を読み込みました。")
            except Exception as e:
                # シークレットアクセスエラーは表示せず、デバッグログのみ記録
                logger.debug(f"シークレットアクセス中の例外（無視します）: {str(e)}")
    except Exception as e:
        logger.debug(f"環境検出中の例外（無視します）: {str(e)}")
    
    # 環境情報と設定方法のガイダンス表示
    if is_env_loaded:
        print("ローカル環境で実行しています。環境変数は.envファイルまたはシステム環境変数から読み込みます。")
    else:
        print("注意: .envファイルが見つかりません。APIキーが設定されていない可能性があります。")
    
    # 設定方法のヒント
    if not "GEMINI_API_KEY" in os.environ:
        print("\nヒント: APIキーを設定するには、以下のいずれかの方法を使用してください:")
        print("1. .envファイルをプロジェクトルートに作成し、GEMINI_API_KEY=your_key_here を追加")
        print("2. .streamlit/secrets.tomlファイルを作成し、GEMINI_API_KEY = \"your_key_here\" を追加")
        print("詳細はSTREAMLIT_DEPLOY.mdを参照してください。\n")
    
    # Streamlit Cloudかどうかのフラグを設定
    if is_streamlit_cloud:
        os.environ["IS_STREAMLIT_CLOUD"] = "true"
    
    return is_streamlit_cloud

# 環境設定を実行
is_streamlit_cloud = setup_environment()

# Streamlit Cloud対応のディレクトリ設定
os.environ["TEMP_DIR"] = tempfile.gettempdir()
os.environ["CACHE_DIR"] = str(root_dir / "cache")
os.environ["LOGS_DIR"] = str(root_dir / "logs")
os.environ["OUTPUT_DIR"] = str(root_dir / "output")

# 必要なディレクトリを作成
required_dirs = [
    "logs",
    "cache",
    "output",
    "assets/samples",
    "assets/templates"
]

for dir_path in required_dirs:
    full_path = root_dir / dir_path
    if not full_path.exists():
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"ディレクトリを作成しました: {full_path}")

# テンプレートファイルの存在確認
template_path = root_dir / "assets" / "templates" / "template.csv"
if not template_path.exists():
    # 実際のアプリケーションによって、テンプレートファイルの初期化方法は変わります
    # ここでは、空のファイルを作成しておく例を示します
    template_path.parent.mkdir(parents=True, exist_ok=True)
    if not template_path.exists():
        template_path.touch()
        print(f"テンプレートファイルを作成しました: {template_path}")

# メインアプリケーションのインポート
from hairstyle_analyzer.data.config_manager import ConfigManager
from hairstyle_analyzer.ui.streamlit_app import run_streamlit_app

if __name__ == "__main__":
    # 設定マネージャーの初期化
    config_manager = ConfigManager("config/config.yaml")
    
    # API設定の確認とガイダンス（警告はUIに表示しない）
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("Gemini APIキーが設定されていません。画像処理機能は動作しません。")
    
    # アプリケーションの実行（ページ設定は既に行われているためskip_page_config=True）
    run_streamlit_app(config_manager, skip_page_config=True) 