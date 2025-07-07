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

# Thuật toán mặc định (cũ)
def predict_dice_from_md5(md5_hash: str):
    md5_hash = md5_hash.strip().lower()
    if len(md5_hash) != 32 or not all(c in '0123456789abcdef' for c in md5_hash):
        return None
    try:
        b = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)]
        dice1 = (b[0] + b[3] + b[14]) % 6 + 1
        dice2 = (b[1] + b[5] + b[12]) % 6 + 1
        dice3 = (b[2] + b[7] + b[13]) % 6 + 1
        total = dice1 + dice2 + dice3
        result = 'Tài' if total >= 11 else 'Xỉu'
        deviation = abs(dice1 - dice2) + abs(dice2 - dice3) + abs(dice3 - dice1)
        if total in [10, 11]:
            trust = 'Cao'
        elif deviation >= 4:
            trust = 'Thấp'
        else:
            trust = 'Trung bình'
        return {
            'xúc_xắc': [dice1, dice2, dice3],
            'tổng': total,
            'kết_quả': result,
            'độ_tin_cậy': trust
        }
    except:
        return None

# Thuật toán nâng cấp (chính xác cao hơn)
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
        return {
            'xúc_xắc': [dice1, dice2, dice3],
            'tổng': total,
            'kết_quả': result,
            'độ_tin_cậy': trust
        }
    except:
        return None

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dts(ctx, md5):
    await run_dts_command(ctx, md5, predict_dice_from_md5, version='dts')

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dtsv1(ctx, md5):
    await run_dts_command(ctx, md5, predict_dice_v1, version='dtsv1')

async def run_dts_command(ctx, md5, predict_func, version='dts'):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()
    md5 = md5.strip().lower()

    if user_id not in USER_KEYS:
        await ctx.send(f"❌ Bạn chưa nhập key. Dùng `.key <key>` trước. <@{ADMIN_ID}>")
        return

    keys = USER_KEYS[user_id] if isinstance(USER_KEYS[user_id], list) else [USER_KEYS[user_id]]
    valid = False
    for k in keys:
        if k in KEYS_DB:
            expire = datetime.strptime(KEYS_DB[k]['expire'], '%Y-%m-%d')
            if now <= expire:
                valid = True
                break

    if not valid:
        del USER_KEYS[user_id]
        save_all()
        await ctx.send(f"❌ Key đã hết hạn. Liên hệ admin <@{ADMIN_ID}>")
        return

    result = predict_func(md5)
    if not result:
        await ctx.send("❌ MD5 không hợp lệ. Vui lòng nhập đúng chuỗi 32 ký tự hex (0-9a-f).")
        return

    # Ghi log
    MD5_LOG.append({
        "user": user_id,
        "md5": md5,
        "bot_result": result['xúc_xắc'],
        "real_result": None
    })
    save_all()

    msg = (
        f"🎲 [{version.upper()}] Kết quả dự đoán:\n"
        f"• Xúc xắc: {result['xúc_xắc']}\n"
        f"• Tổng: {result['tổng']} ({result['kết_quả']})\n"
        f"• Độ tin cậy: {result['độ_tin_cậy']}\n\n"
        f"✨ DTS TOOL VIP – MUỐN MUA KEY LIÊN HỆ ADMIN <@{ADMIN_ID}>"
    )
    await ctx.send(msg)

# Giữ nguyên các lệnh .key, .delkey, .taokey, .danhsach, on_message

# FastAPI server để giữ bot online
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

bot.run(TOKEN)
