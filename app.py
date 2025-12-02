from flask import Flask, request, abort
from datetime import datetime, timedelta, timezone
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from pathlib import Path
import csv
import os

# 環境変数からチャネル情報を取得（Render の Environment Variables で設定済み）
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

JST = timezone(timedelta(hours=9))


def load_station_minutes() -> dict[str, int]:
    """
    同じディレクトリに置いた CSV から
    「駅名 → 妙典までの所要時間（分）」の辞書を作る。
    CSV 形式（ヘッダーなしでOK）:
        駅名,分
        中野,47
        落合,45
        ...
    """
    base_dir = Path(__file__).resolve().parent
    csv_path = base_dir / "LINE API - シート1.csv"  # ← スプシから保存したファイル名に合わせる

    station_map: dict[str, int] = {}

    try:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) < 2:
                    continue
                name = str(row[0]).strip()
                minutes_str = str(row[1]).strip()
                if not name or not minutes_str:
                    continue
                try:
                    minutes = int(minutes_str)
                except ValueError:
                    # 数字でない行はスキップ（ヘッダー入れても大丈夫）
                    continue
                station_map[name] = minutes
    except FileNotFoundError:
        # CSV がないときは空のまま（全部無視される）
        pass

    return station_map


STATION_TO_MINUTES = load_station_minutes()


@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    text = event.message.text.strip()

    # ③ 「＠駅名」 or 「@駅名」以外は完全無視
    if text.startswith("＠") or text.startswith("@"):
        station_name = text[1:].strip()
    else:
        # 何も返信しない
        return

    # ① CSV から読み込んだ辞書を使用
    minutes = STATION_TO_MINUTES.get(station_name)

    # ② CSV に無い駅名 → 返信しない
    if minutes is None:
        return

    now = datetime.now(JST)
    arrival = now + timedelta(minutes=minutes)
    arrival_str = arrival.strftime("%H:%M")

    reply_text = f"{station_name}から妙典までは約{minutes}分です。\n{arrival_str}ごろに到着予定です。"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text),
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
