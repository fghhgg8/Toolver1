import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json, os
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

USER_KEYS = {}  # user_id: key hoặc list
KEYS_DB = {}    # key: {expire: yyyy-mm-dd}

# Load dữ liệu từ file
if os.path.exists(USER_KEYS_FILE):
    with open(USER_KEYS_FILE, 'r') as f:
        USER_KEYS = json.load(f)

if os.path.exists(KEYS_DB_FILE):
    with open(KEYS_DB_FILE, 'r') as f:
        KEYS_DB = json.load(f)

# Lưu dữ liệu
def save_all():
    with open(USER_KEYS_FILE, 'w') as f:
        json.dump(USER_KEYS, f, indent=4)
    with open(KEYS_DB_FILE, 'w') as f:
        json.dump(KEYS_DB, f, indent=4)

# Thuật toán dự đoán từ MD5
def predict_dice_from_md5(md5_hash: str):
    if len(md5_hash) != 32:
        return None
    if not all(c in '0123456789abcdefABCDEF' for c in md5_hash):
        return None
    try:
        b = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)]
        if len(b) < 18:
            return None

        dice1 = ((b[1] + b[3] + b[5]) // 3) % 6 + 1
        dice2 = ((b[7] + b[9] + b[11]) // 3) % 6 + 1
        dice3 = ((b[13] + b[15] + b[17]) // 3) % 6 + 1

        total = dice1 + dice2 + dice3
        result = 'Tài' if total >= 11 else 'Xỉu'

        trust = 'Trung bình'
        if total in [10, 11]:
            trust = 'Cao'
        elif total <= 8 or total >= 13:
            trust = 'Thấp'

        return {
            'xúc_xắc': [dice1, dice2, dice3],
            'tổng': total,
            'kết_quả': result,
            'độ_tin_cậy': trust
        }
    except Exception as e:
        print(f"Lỗi dự đoán MD5: {e}")
        return None

# Lệnh nhập key
@bot.command()
async def key(ctx, key):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    if key not in KEYS_DB:
        await ctx.send(f"❌ Key không tồn tại. Liên hệ admin <@{ADMIN_ID}>")
        return

    expire = datetime.strptime(KEYS_DB[key]['expire'], '%Y-%m-%d')
    if now > expire:
        await ctx.send(f"❌ Key đã hết hạn. Liên hệ admin <@{ADMIN_ID}>")
        return

    if ctx.author.id == ADMIN_ID:
        USER_KEYS[user_id] = USER_KEYS.get(user_id, [])
        if key not in USER_KEYS[user_id]:
            USER_KEYS[user_id].append(key)
            save_all()
        await ctx.send("✅ Admin nhập key thành công.")
        return

    if user_id in USER_KEYS:
        await ctx.send("✅ Bạn đã nhập key rồi.")
        return

    for uid, keys in USER_KEYS.items():
        if (isinstance(keys, list) and key in keys) or keys == key:
            await ctx.send(f"❌ Key đã được người khác sử dụng. Liên hệ admin <@{ADMIN_ID}>")
            return

    USER_KEYS[user_id] = key
    save_all()
    await ctx.send("✅ Key xác nhận thành công. Dùng lệnh `.dts <md5>`")

# Lệnh dự đoán
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dts(ctx, md5):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

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

    result = predict_dice_from_md5(md5)
    if not result:
        await ctx.send("❌ MD5 không hợp lệ. Vui lòng nhập đúng mã MD5 32 ký tự hex (0-9a-f).")
        return

    msg = (
        f"🎲 Kết quả dự đoán:\n"
        f"• Xúc xắc: {result['xúc_xắc']}\n"
        f"• Tổng: {result['tổng']} ({result['kết_quả']})\n"
        f"• Độ tin cậy: {result['độ_tin_cậy']}\n\n"
        f"✨ DTS TOOL VIP – MUỐN MUA KEY LIÊN HỆ ADMIN <@{ADMIN_ID}>"
    )
    await ctx.send(msg)

# Admin tạo key
@bot.command()
async def taokey(ctx, ten: str, songay: int):
    if ctx.author.id != ADMIN_ID:
        return
    key = ten.lower()
    expire_date = (datetime.utcnow() + timedelta(days=songay)).strftime('%Y-%m-%d')
    KEYS_DB[key] = {'key': key, 'expire': expire_date}
    save_all()
    await ctx.send(f"✨ Key `{key}` đã tạo, hết hạn ngày {expire_date}")

# Xóa key người dùng
@bot.command()
async def delkey(ctx):
    user_id = str(ctx.author.id)
    if user_id in USER_KEYS:
        del USER_KEYS[user_id]
        save_all()
        await ctx.send("✅ Key đã xóa. Nhập key mới.")
    else:
        await ctx.send("⚠️ Bạn chưa nhập key.")

# FastAPI cho UptimeRobot
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

# Khởi động bot
bot.run(TOKEN)
