from flask import Flask, request, abort
from datetime import datetime, timedelta, timezone
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "YOUR_CHANNEL_SECRET")
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "YOUR_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

app = Flask(__name__)

STATION_TO_MINUTES = {
    "大手町": 30,
    "日本橋": 28,
    "茅場町": 25,
    "門前仲町": 20,
    "東陽町": 15,
    "西葛西": 8,
    "葛西": 5,
    "妙典": 0,
}

JST = timezone(timedelta(hours=9))

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
    user_text = event.message.text.strip()
    if user_text in STATION_TO_MINUTES:
        minutes = STATION_TO_MINUTES[user_text]
        now = datetime.now(JST)
        arrival = now + timedelta(minutes=minutes)
        arrival_str = arrival.strftime("%H:%M")
        reply_text = f"{arrival_str}に到着予定です（{minutes}分後）"
    else:
        reply_text = f"未登録駅です。辞書に追加してください"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
