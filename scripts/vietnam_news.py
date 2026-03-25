import anthropic
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

JST = timezone(timedelta(hours=9))
today = datetime.now(JST).strftime("%Y年%m月%d日")

GOOGLE_CHAT_WEBHOOK = (
    "https://chat.googleapis.com/v1/spaces/AAQABlnoogA/messages"
    "?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI"
    "&token=QRl97QRTgFVLeLyjQHzM_IIXJQLtsyDVVcFBrJoz4Cs"
)

PROMPT = f"""あなたは飲食業界のニュースキュレーターです。今日の日付は {today} です。

## タスク
前日のベトナムに関連するニュースを検索・収集し、飲食業経営者が必ず目を通すべき情報をまとめたメッセージを作成してください。

## Step 1: ニュース検索
以下のキーワードでWeb検索を行い、最新ニュースを収集してください（複数検索を実行）：

- "Vietnam food restaurant industry news"
- "ベトナム 飲食 外食 ニュース 最新"
- "Vietnam economy consumer spending food"
- "Ho Chi Minh Hanoi restaurant regulation food safety"
- "Vietnam inflation food price latest"
- "ベトナム 物価 外食産業 規制 最新"
- "Vietnam law regulation business update latest"
- "ベトナム 法律 改正 ビジネス 最新"
- "global trade tariff food supply chain restaurant impact"
- "world economy geopolitical risk food business"

## Step 2: 情報の選別
以下のカテゴリに関するニュースを優先して選定してください：
- 食品・衛生規制の変更
- 最低賃金・労働法の改定
- 食材・原材料の価格動向
- 外食産業のトレンド・消費者動向
- 観光客数・インバウンド動向
- 競合チェーンの動向（外資系含む）
- 税制・ライセンス・営業許可に関する法改正
- ベトナム経済全般（GDP・インフレ・為替）
- ベトナムの法律全般（会社法・外資規制・労働法・環境法・知的財産など、飲食業に影響しうる改正・施行）
- 世界情勢で経営に影響するもの（貿易摩擦・関税・地政学リスク・食材サプライチェーン混乱・エネルギー価格・主要国の経済政策など）

## Step 3: メッセージ作成
以下のフォーマットでメッセージを作成してください。最終的な出力はこのメッセージ本文のみにしてください：

🇻🇳 *ベトナム飲食経営者向け 日次ニュース* — {today}

━━━━━━━━━━━━━━━━━━

📌 *本日のハイライト*
（最重要ニュース1〜2件を1行で要約）

━━━━━━━━━━━━━━━━━━

{{カテゴリ絵文字}} *{{カテゴリ名}}*
• {{ニュース要約（2〜3文）}}
　→ {{なぜ飲食経営者に重要か、一言で}}
　🔗 {{ソースURL}}

（上記を3〜6件繰り返し）

━━━━━━━━━━━━━━━━━━
📊 *経営への示唆*
（全ニュースを踏まえた、今週注意すべき点を2〜3点箇条書き）

カテゴリ絵文字の例：
- 📋 規制・法律
- ⚖️ ベトナム法律アップデート
- 💰 価格・経済
- 👥 労働・人材
- 🍽️ 外食トレンド
- ✈️ 観光・インバウンド
- 🏪 競合・市場
- 🌏 世界情勢・経営への影響

ニュースが見つからない場合は、直近1週間の重要トピックで代替してください。"""


def run_news_agent():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    tools = [{"type": "web_search_20250305", "name": "web_search"}]
    messages = [{"role": "user", "content": PROMPT}]

    print("Searching for Vietnam news...")
    while True:
        response = client.beta.messages.create(
            model="claude-opus-4-6",
            max_tokens=4096,
            tools=tools,
            messages=messages,
            betas=["web-search-2025-03-05"],
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"  Searching: {getattr(block.input, 'query', block.input)}")
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": [],
                })
        messages.append({"role": "user", "content": tool_results})

    final_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            final_text = block.text

    return final_text


def send_to_google_chat(text):
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        GOOGLE_CHAT_WEBHOOK,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        status = resp.status
        print(f"Google Chat response: {status}")
        return status


if __name__ == "__main__":
    message = run_news_agent()
    if not message:
        print("ERROR: No message generated", file=sys.stderr)
        sys.exit(1)

    print("\n--- Generated message preview (first 200 chars) ---")
    print(message[:200] + "...")

    status = send_to_google_chat(message)
    if status != 200:
        print(f"ERROR: Google Chat returned {status}", file=sys.stderr)
        sys.exit(1)

    print("Done.")
