"""
ヘアスタイル画像解析システムのエントリーポイント
"""
import streamlit.web.cli as stcli
import sys
from pathlib import Path
import os

# プロジェクトルートをPythonパスに追加
root_dir = Path(__file__).parent
sys.path.append(str(root_dir))

# アプリケーションのパス
app_path = root_dir / "hairstyle_analyzer" / "ui" / "streamlit_app.py"

if __name__ == "__main__":
    # 環境変数を設定
    os.environ["PYTHONPATH"] = str(root_dir)
    
    # Streamlitアプリを実行
    sys.argv = ["streamlit", "run", str(app_path), "--browser.serverAddress", "localhost", "--server.port", "8501"]
    sys.exit(stcli.main()) 