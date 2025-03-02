# Gemini API 構造化出力のサンプル

このドキュメントはGoogle Gemini APIを使用して構造化出力を生成するためのサンプルコードを提供します。

## 基本的な構造化出力の使用方法

```python
import google.generativeai as genai
import json
import os
from dotenv import load_dotenv

# 環境変数からAPIキーを読み込む
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Gemini APIの設定
genai.configure(api_key=GEMINI_API_KEY)

# モデルの初期化
model = genai.GenerativeModel('gemini-2.0-flash')

# プロンプトの作成
prompt = """
この画像のヘアスタイルを分析し、以下の情報をJSON形式で返してください:

1. カテゴリ (以下から1つだけ選択してください):
- 最新トレンド
- 髪質改善
- ショート・ボブ
- ミディアム・セミロング
- ロング
- メンズ

2. 特徴:
   - 髪色: 色調や特徴を詳しく
   - カット技法: レイヤー、グラデーション、ボブなど
   - スタイリング: ストレート、ウェーブ、パーマなど
   - 印象: フェミニン、クール、ナチュラルなど

必ず以下のJSON形式で出力してください:
{
  "category": "カテゴリ名",
  "features": {
    "color": "詳細な色の説明",
    "cut_technique": "カット技法の説明",
    "styling": "スタイリング方法の説明",
    "impression": "全体的な印象"
  },
  "keywords": ["キーワード1", "キーワード2", "キーワード3"]
}
"""

# 画像データの準備
def encode_image(image_path):
    import base64
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# 画像パス
image_path = "path/to/your/image.jpg"
encoded_image = encode_image(image_path)

# 画像コンテンツの作成
image_parts = {
    "mime_type": "image/jpeg", 
    "data": encoded_image
}

# APIリクエストの実行
response = model.generate_content(
    [prompt, image_parts],
    generation_config={
        "response_mime_type": "application/json"
    }
)

# レスポンスの処理
try:
    # JSON文字列としてレスポンスを取得
    json_response = response.text
    # JSONをPythonオブジェクトに変換
    result = json.loads(json_response)
    
    # 結果の表示
    print("カテゴリ:", result["category"])
    print("特徴:")
    for key, value in result["features"].items():
        print(f"  - {key}: {value}")
    print("キーワード:", ", ".join(result["keywords"]))
    
except json.JSONDecodeError:
    print("JSONのパースに失敗しました。レスポンス:", response.text)
except Exception as e:
    print(f"エラーが発生しました: {e}")
```

## 属性分析用のサンプルコード

```python
# 属性分析（性別と髪の長さ）用のプロンプト
attribute_prompt = """
この画像のヘアスタイルの性別と髪の長さを判定してください。

性別は「レディース」または「メンズ」のいずれかを選択してください。
髪の長さは以下の選択肢から最も適切なものを選んでください:
- ベリーショート
- ショート
- ミディアム
- セミロング
- ロング
- ヘアセット
- ミセス

必ず以下のJSON形式で出力してください:
{
  "sex": "性別",
  "length": "髪の長さ"
}
"""

# APIリクエストの実行
attribute_response = model.generate_content(
    [attribute_prompt, image_parts],
    generation_config={
        "response_mime_type": "application/json"
    }
)

# レスポンスの処理
try:
    attribute_result = json.loads(attribute_response.text)
    print(f"性別: {attribute_result['sex']}")
    print(f"髪の長さ: {attribute_result['length']}")
except Exception as e:
    print(f"エラー: {e}")
```

## 非同期処理でのGemini API呼び出し

```python
import asyncio

async def analyze_image_with_gemini(image_path, prompt):
    # 画像データの準備
    encoded_image = encode_image(image_path)
    image_parts = {
        "mime_type": "image/jpeg", 
        "data": encoded_image
    }
    
    # 非同期でAPIを呼び出し
    response = await asyncio.to_thread(
        model.generate_content,
        [prompt, image_parts],
        generation_config={
            "response_mime_type": "application/json"
        }
    )
    
    # JSONとしてパース
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        raise ValueError(f"JSONのパースに失敗しました: {response.text}")

# 使用例
async def main():
    result = await analyze_image_with_gemini("path/to/image.jpg", prompt)
    print(result)

# イベントループの実行
if __name__ == "__main__":
    asyncio.run(main())
```

## エラーハンドリングとリトライ

```python
async def analyze_image_with_retry(image_path, prompt, max_retries=3, retry_delay=1):
    for attempt in range(max_retries):
        try:
            return await analyze_image_with_gemini(image_path, prompt)
        except Exception as e:
            if attempt < max_retries - 1:
                # リトライ前に待機
                await asyncio.sleep(retry_delay * (attempt + 1))
                continue
            raise  # 最大リトライ回数に達したら例外を投げる
```

## フォールバックモデルの使用

```python
async def analyze_image_with_fallback(image_path, prompt):
    # プライマリモデルの設定
    primary_model = genai.GenerativeModel('gemini-2.0-flash')
    
    # フォールバックモデルの設定
    fallback_model = genai.GenerativeModel('gemini-2.0-flash-lite')
    
    try:
        # プライマリモデルでの分析を試みる
        response = await asyncio.to_thread(
            primary_model.generate_content,
            [prompt, image_parts],
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        return json.loads(response.text)
    except Exception as e:
        # エラーが発生した場合はフォールバックモデルを使用
        print(f"プライマリモデルでのエラー: {e}, フォールバックモデルを使用します")
        response = await asyncio.to_thread(
            fallback_model.generate_content,
            [prompt, image_parts],
            generation_config={
                "response_mime_type": "application/json"
            }
        )
        return json.loads(response.text)
```

## 注意点

1. API呼び出しの前に必ず `response_mime_type` を指定しましょう。これにより、モデルに構造化された出力を生成するよう指示できます。

2. レスポンスは常に `json.loads()` を使用して検証し、エラーハンドリングを適切に行いましょう。

3. プロンプトでは、期待するJSON構造を明確に示すことが重要です。

4. 非同期処理を使用して複数の画像を並行処理する場合は、レート制限に注意しましょう。

5. 画像サイズは大きすぎると処理時間やAPIの制限に影響するため、適切なサイズに調整することをお勧めします。
