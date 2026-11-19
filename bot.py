import os, base64, threading
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI

# Fake website for Render Free
app_web = Flask(__name__)
@app_web.route('/')
def home():
    return "A1 Trade AI is LIVE"

def run_web():
    app_web.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)
user_photos = {}

A1_PROMPT = """
You are A1 TRADE AI, expert Gold & EURUSD trader.
You receive 4 charts in order: 1. Daily, 2. 4H, 3. 15M, 4. 1M
LOCKED RULES:
- Only XAUUSD and EURUSD
- Daily = bias. Do NOT trade against Daily.
- 4H must show trend / Break of Structure
- 15M must show retest at Order Block / FVG / Support-Resistance. Do NOT chase.
- 1M must show small confirmation.
RISK REWARD LOCKED:
- TP1 MUST be 1:1. If SL is 50 pips, TP1 must be 50 pips.
- TP2 AIM for 1:2. But if market only allows 1:1.2, 1:1.3, 1:1.4, 1:1.5, GIVE THAT VALUE. DO NOT SAY NO TRADE because TP2 is not 1:2.
- If TP1 cannot be 1:1, say NO VALID SETUP.
OUTPUT EXACTLY LIKE THIS:
PAIR:
BIAS: BULLISH / BEARISH / NO TRADE
ENTRY:
SL:
TP1: (1:1)
TP2: (1:X)
CONFIDENCE: %
WHY: 2 lines max
NOTE: Move SL to breakeven after TP1 hit.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_photos[update.effective_user.id] = []
    await update.message.reply_text("Welcome to A1 TRADE AI ✅\n\nSend 4 charts in order:\n1. Daily\n2. 4H\n3. 15M\n4. 1M")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in user_photos:
        user_photos[user_id] = []
    photo = await update.message.photo[-1].get_file()
    path = f"temp_{user_id}_{len(user_photos[user_id])}.jpg"
    await photo.download_to_drive(path)
    user_photos[user_id].append(path)
    labels = ["Daily", "4H", "15M", "1M"]
    count = len(user_photos[user_id])
    if count < 4:
        await update.message.reply_text(f"{labels[count-1]} ✅ received. Send next: {labels[count]}")
        return
    await update.message.reply_text("All 4 received. A1 Trade AI dey analyze... ⏳ 20 secs")
    images_content = []
    for p in user_photos[user_id]:
        with open(p, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            images_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        try: os.remove(p)
        except: pass
    try:
        response = client.chat.completions.create(model="gpt-4o", messages=[{"role": "system", "content": A1_PROMPT}, {"role": "user", "content": [{"type": "text", "text": "Analyze these 4 charts in order Daily, 4H, 15M, 1M and give trade plan."}] + images_content}], max_tokens=800)
        result = response.choices[0].message.content
    except Exception as e:
        result = f"Error analyzing. Try again. Details: {e}"
    await update.message.reply_text(result)
    user_photos[user_id] = []

if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("A1 Trade AI is LIVE...")
    app.run_polling()
