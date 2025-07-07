import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json, os, re
from fastapi import FastAPI
import uvicorn
import threading

# Config
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID = 1115314183731421274
PREFIX = '.'

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

USER_KEYS_FILE = 'user_keys.json'
KEYS_DB_FILE = 'keys_db.json'
MD5_LOG_FILE = 'md5_log.json'

USER_KEYS = {}
KEYS_DB = {}
MD5_LOG = []

if os.path.exists(USER_KEYS_FILE):
    with open(USER_KEYS_FILE, 'r') as f:
        USER_KEYS = json.load(f)

if os.path.exists(KEYS_DB_FILE):
    with open(KEYS_DB_FILE, 'r') as f:
        KEYS_DB = json.load(f)

if os.path.exists(MD5_LOG_FILE):
    with open(MD5_LOG_FILE, 'r') as f:
        MD5_LOG = json.load(f)

def save_all():
    with open(USER_KEYS_FILE, 'w') as f:
        json.dump(USER_KEYS, f, indent=4)
    with open(KEYS_DB_FILE, 'w') as f:
        json.dump(KEYS_DB, f, indent=4)
    with open(MD5_LOG_FILE, 'w') as f:
        json.dump(MD5_LOG, f, indent=4)

def predict_dice_from_md5(md5_hash: str):
    try:
        md5_hash = md5_hash.strip().lower()
        if len(md5_hash) != 32 or not all(c in '0123456789abcdef' for c in md5_hash):
            return None
        b = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)]
        dice1 = (b[0] + b[3] + b[14]) % 6 + 1
        dice2 = (b[1] + b[5] + b[12]) % 6 + 1
        dice3 = (b[2] + b[7] + b[13]) % 6 + 1
        total = dice1 + dice2 + dice3
        result = 'Tài' if total >= 11 else 'Xỉu'
        deviation = abs(dice1 - dice2) + abs(dice2 - dice3) + abs(dice3 - dice1)
        trust = 'Cao' if total in [10, 11] else 'Thấp' if deviation >= 4 else 'Trung bình'
        return {'xúc_xắc': [dice1, dice2, dice3], 'tổng': total, 'kết_quả': result, 'độ_tin_cậy': trust}
    except:
        return None

def predict_dice_v1(md5_hash: str):
    try:
        md5_hash = md5_hash.strip().lower()
        if len(md5_hash) != 32 or not all(c in '0123456789abcdef' for c in md5_hash):
            return None
        b = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)]
        dice1 = (b[0] ^ b[6] ^ b[11]) % 6 + 1
        dice2 = (b[1] ^ b[5] ^ b[10]) % 6 + 1
        dice3 = (b[2] ^ b[7] ^ b[12]) % 6 + 1
        total = dice1 + dice2 + dice3
        result = 'Tài' if total >= 11 else 'Xỉu'
        deviation = abs(dice1 - dice2) + abs(dice2 - dice3) + abs(dice3 - dice1)
        trust = 'Cao' if total in [10, 11] else 'Thấp' if deviation >= 4 else 'Trung bình'
        return {'xúc_xắc': [dice1, dice2, dice3], 'tổng': total, 'kết_quả': result, 'độ_tin_cậy': trust}
    except:
        return None

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if bot.user in message.mentions and message.author.id == ADMIN_ID:
        warning = (
            "⚠️ **BOT VẪN LÀ BOT KHÔNG THỂ CHÍNH XÁC 100%**. NẾU ĐÚNG 100% AD ĐÃ GIÀU\n"
            "**KHÔNG NÊN ALLIN, ALLIN = CÚT, TRÁNH CẦU BỆT**\n"
            "**NHẮC LẠI BOT VẪN LÀ BOT KHÔNG THỂ CHÍNH XÁC 100%, ĐÔI LÚC CHỈ ĐÚNG 60%-70%**\n"
            "💡 **LƯU Ý: CỜ BẠC CHÁN CHÁN THÌ CHƠI VUI VUI, KHÔNG NÊN HAM. HAM QUÁ MẤT NHÀ!**\n"
            "❌ **CỜ BẠC LÀ HÀNH VI VI PHẠM PHÁP LUẬT. KHÔNG CỔ SÚY CHƠI!**"
        )
        await message.channel.send(warning)
    await bot.process_commands(message)

@bot.command()
async def key(ctx, key):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    if key not in KEYS_DB or KEYS_DB[key].get("type") != "dts":
        await ctx.send(f"❌ Key không tồn tại hoặc sai loại. Liên hệ admin <@{ADMIN_ID}>")
        return

    expire = datetime.strptime(KEYS_DB[key]['expire'], '%Y-%m-%d')
    if now > expire:
        await ctx.send(f"❌ Key đã hết hạn. Liên hệ admin <@{ADMIN_ID}>")
        return

    USER_KEYS.setdefault(user_id, {})

    if ctx.author.id == ADMIN_ID:
        USER_KEYS[user_id].setdefault("dts", [])
        if key not in USER_KEYS[user_id]["dts"]:
            USER_KEYS[user_id]["dts"].append(key)
        save_all()
        await ctx.send("✅ Admin đã thêm key thành công.")
        return

    if "dts" in USER_KEYS[user_id]:
        await ctx.send("✅ Bạn đã nhập key rồi.")
        return

    for uid, keys in USER_KEYS.items():
        if keys.get("dts") == key:
            await ctx.send(f"❌ Key đã được người khác sử dụng. Liên hệ admin <@{ADMIN_ID}>")
            return

    USER_KEYS[user_id]["dts"] = key
    save_all()
    await ctx.send("✅ Nhập key thành công.")

@bot.command()
async def taokeydts(ctx, key: str, days: int):
    if ctx.author.id != ADMIN_ID:
        return
    expire_date = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d')
    KEYS_DB[key] = {"expire": expire_date, "type": "dts"}
    save_all()
    await ctx.send(f"✅ Đã tạo key `{key}` cho `.dts`, hết hạn vào {expire_date}")

@bot.command()
async def dts(ctx, md5: str):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    if user_id not in USER_KEYS or "dts" not in USER_KEYS[user_id]:
        await ctx.send(f"❌ Bạn chưa nhập key. Dùng `.key <key>` trước. <@{ADMIN_ID}>")
        return

    keys = USER_KEYS[user_id]["dts"]
    if isinstance(keys, str):
        keys = [keys]

    valid = False
    for key in keys:
        if key in KEYS_DB and datetime.strptime(KEYS_DB[key]['expire'], '%Y-%m-%d') >= now:
            valid = True
            break

    if not valid:
        del USER_KEYS[user_id]["dts"]
        save_all()
        await ctx.send(f"❌ Key đã hết hạn. Liên hệ admin <@{ADMIN_ID}>")
        return

    result = predict_dice_from_md5(md5)
    if not result:
        await ctx.send("❌ MD5 không hợp lệ.")
        return

    MD5_LOG.append({
        "user": user_id,
        "md5": md5,
        "bot_result": result['xúc_xắc'],
        "real_result": None,
        "version": "dts"
    })
    save_all()

    msg = (
        f"🎲 [DTS] Kết quả dự đoán:\n"
        f"• Xúc xắc: {result['xúc_xắc']}\n"
        f"• Tổng: {result['tổng']} ({result['kết_quả']})\n"
        f"• Độ tin cậy: {result['độ_tin_cậy']}\n\n"
        f"✨ DTS TOOL VIP – MUỐN MUA KEY LIÊN HỆ ADMIN <@{ADMIN_ID}>"
    )
    await ctx.send(msg)

# FastAPI giữ bot online
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

bot.run(TOKEN)
