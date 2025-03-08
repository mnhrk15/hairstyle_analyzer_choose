# Streamlit Cloudデプロイ手順

このドキュメントでは、ヘアスタイル画像解析システムをStreamlit Cloudにデプロイする手順と注意点を説明します。

## 1. 前準備

### 1.1 GitHubリポジトリの準備

1. GitHubアカウントにログインする
2. 新しいリポジトリを作成する（プライベートリポジトリ推奨）
3. ローカルのプロジェクトをリポジトリにプッシュする

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/your-username/hairstyle_analyzer.git
git push -u origin main
```

### 1.2 APIキーの管理

`.env`ファイルに含まれているAPIキー（GEMINI_API_KEY）はGitHubにプッシュしないでください。
代わりにStreamlit Cloudのシークレット機能を使用します。

**重要**: セキュリティ強化のため、アプリケーションのGUIからAPIキーを設定する機能は削除されました。APIキーは必ずStreamlit Cloudのシークレット機能を使用して設定してください。

## 2. Streamlit Cloudでのデプロイ手順

### 2.1 Streamlit Cloudアカウントの作成

1. [Streamlit Cloud](https://streamlit.io/cloud)にアクセスする
2. GitHubアカウントでサインインする

### 2.2 新しいアプリをデプロイする

1. 「New app」ボタンをクリックする
2. リポジトリを選択する
3. ブランチを選択する（通常は「main」）
4. メインモジュールには「app.py」を指定する（以前は「streamlit_app.py」でしたが変更されました）
5. 「Deploy!」ボタンをクリックする

### 2.3 シークレットの設定

1. デプロイしたアプリの「⋮」（三点メニュー）をクリックする
2. 「Settings」を選択する
3. 「Secrets」セクションで以下のシークレットを追加する

```
GEMINI_API_KEY=your_api_key_here
HOTPEPPER_URL=https://beauty.hotpepper.jp/slnH000000000/
```

必要に応じて他の環境変数も追加してください。

## 3. 注意点

### 3.1 ファイルシステムの制限

Streamlit Cloudは読み取り専用ファイルシステムを使用しています。そのため：

- アプリケーションの実行中に作成されたファイルは永続化されません
- 起動時に必要なディレクトリ（logs, cache, output, tempなど）は自動的に作成されます
- キャッシュファイルは各デプロイで初期化されます

#### 3.1.1 一時ファイルの扱い

アプリケーションは以下のように一時ファイルを処理します：

- 画像のアップロードにはPythonの標準的な一時ディレクトリ（`tempfile.gettempdir()`）を使用
- 一時ファイルはセッション終了時に自動的に削除される可能性があります
- エクスポートしたいファイルはユーザーがダウンロードする必要があります

#### 3.1.2 ログファイル

Streamlit Cloud環境では以下のようにログが扱われます：

- コンソールログはStreamlit Cloudのログビューアで確認可能
- ファイルへのログ出力は限定的（読み取り専用ファイルシステムのため）
- 重要なエラーはUI上に表示されます

### 3.2 環境変数とAPIキー

Streamlit Cloudでは、`.env`ファイルの代わりにシークレット機能を使用します。
シークレットの値は`st.secrets`を通じてアクセスできます。

```python
import streamlit as st

# シークレットにアクセスする例
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"]
```

セキュリティ上の理由から、Gemini APIキーはアプリケーションのGUI上に表示されなくなりました。
APIキーの変更が必要な場合は、必ずStreamlit Cloudの管理画面からシークレットを更新してください。

### 3.3 リソース制限

Streamlit Cloudには以下のリソース制限があります：

- メモリ制限: 8GB（コミュニティティア）
- ディスク容量: 読み取り専用
- セッション: 最大1時間のアイドルタイムアウト

### 3.4 Gemini APIの利用について

Google Cloud PlatformのGemini APIは利用制限があります。高トラフィックが予想される場合は、適切なAPIキーの管理と制限の設定を検討してください。

## 4. トラブルシューティング

### 4.1 アプリがクラッシュする場合

1. Streamlit Cloudのログを確認する
2. 環境変数（シークレット）が正しく設定されているか確認する
3. 必要なディレクトリが作成されているか確認する

### 4.2 画像のアップロードに問題がある場合

- 画像サイズの制限を確認する（Streamlit Cloudでは最大200MB）
- 一時ディレクトリへの書き込み権限を確認する
- 特殊文字を含むファイル名は問題を引き起こす可能性があります

### 4.3 APIリクエストのエラー

- APIキーが正しく設定されているか確認する
- レート制限に達していないか確認する
- タイムアウト設定を調整する

## 5. アップデート方法

GitHubリポジトリに変更をプッシュすると、Streamlit Cloudは自動的にアプリケーションを再デプロイします。

```bash
git add .
git commit -m "Update app"
git push origin main
```

## 6. ローカル開発と実行

### 6.1 ローカル開発時のコマンド

アプリケーションをローカルで実行する際には以下のコマンドを使用します：

```bash
# 開発環境での実行（推奨）
streamlit run app.py

# 従来の起動方法（必要に応じて）
python run_app.py
```

### 6.2 ローカル環境でのシークレット設定

ローカル環境でStreamlitのシークレット機能を使用する場合は、以下の2つの方法があります：

#### 方法1: .envファイルを使用する（推奨）
プロジェクトのルートディレクトリに`.env`ファイルを作成し、必要な環境変数を設定します：

```
GEMINI_API_KEY=your_api_key_here
HOTPEPPER_URL=https://beauty.hotpepper.jp/slnH000000000/
```

#### 方法2: Streamlitのシークレットファイルを使用する
ローカル環境でStreamlitのシークレット機能を使用する場合は、`.streamlit/secrets.toml`ファイルを作成します：

1. プロジェクトルートまたはホームディレクトリに`.streamlit`ディレクトリを作成
   ```bash
   mkdir -p .streamlit
   ```

2. その中に`secrets.toml`ファイルを作成
   ```bash
   touch .streamlit/secrets.toml
   ```

3. 以下の内容を追加
   ```toml
   # .streamlit/secrets.toml
   
   GEMINI_API_KEY = "your_api_key_here"
   HOTPEPPER_URL = "https://beauty.hotpepper.jp/slnH000000000/"
   ```

この方法を使うと、`st.secrets`を通じて直接シークレットにアクセスできます。

### 6.3 ファイル構造について

アプリケーションでは以下のファイルが重要な役割を持ちます：

- `app.py`: Streamlit Cloudデプロイ用のエントリーポイント（以前は `streamlit_app.py`）
- `run_app.py`: 従来の起動スクリプト
- `hairstyle_analyzer/ui/streamlit_app.py`: アプリケーションの実際の実装

## 7. 参考リンク

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-cloud/get-started/deploy-an-app/connect-to-data-sources/secrets-management) 