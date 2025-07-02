import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os
import random
from flask import Flask
from threading import Thread

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

ADMIN_IDS = [1115314183731421274]  # Thay bằng ID của bạn

KEYS_FILE = "keys.json"
VERIFIED_USERS_FILE = "verified_users.json"

# ------------------ JSON Functions --------------------
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ KEY FUNCTIONS ---------------------
def add_key(key):
    keys = load_json(KEYS_FILE)
    expiry = datetime.utcnow() + timedelta(days=30)
    keys[key] = expiry.isoformat()
    save_json(KEYS_FILE, keys)
    return expiry

def is_key_valid(key):
    keys = load_json(KEYS_FILE)
    if key in keys:
        expiry = datetime.fromisoformat(keys[key])
        return datetime.utcnow() < expiry
    return False

def save_verified_user(user_id, expiry):
    users = load_json(VERIFIED_USERS_FILE)
    users[str(user_id)] = expiry.isoformat()
    save_json(VERIFIED_USERS_FILE, users)

def is_user_verified(user_id):
    users = load_json(VERIFIED_USERS_FILE)
    uid = str(user_id)
    if uid in users:
        expiry = datetime.fromisoformat(users[uid])
        return datetime.utcnow() < expiry
    return False

# ------------------ BOT COMMANDS ----------------------

@bot.command()
async def addkey(ctx, key: str = None):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Bạn không có quyền tạo key.")
    if not key:
        return await ctx.send("⚠️ Dùng đúng: `.addkey <key>`")

    expiry = add_key(key)
    await ctx.send(f"✅ Key `{key}` có hiệu lực đến `{expiry.date()}` (UTC)")

@bot.command()
async def delkey(ctx, key: str = None):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Bạn không có quyền xóa key.")
    
    if not key:
        return await ctx.send("⚠️ Dùng đúng cú pháp: `.delkey <key>`")

    keys = load_json(KEYS_FILE)
    if key in keys:
        del keys[key]
        save_json(KEYS_FILE, keys)
        await ctx.send(f"🗑️ Đã xóa key `{key}`.")
    else:
        await ctx.send("❌ Key không tồn tại.")

@bot.command()
async def key(ctx, key: str = None):
    if not key:
        return await ctx.send("⚠️ Dùng đúng: `.key <key>`")

    if is_key_valid(key):
        expiry = load_json(KEYS_FILE)[key]
        save_verified_user(ctx.author.id, datetime.fromisoformat(expiry))
        await ctx.send("✅ Key hợp lệ! Giờ bạn có thể dùng `.toolvip <md5>`")
    else:
        await ctx.send("🔒 Key không hợp lệ hoặc đã hết hạn.")

@bot.command()
async def toolvip(ctx, md5: str = None):
    if not is_user_verified(ctx.author.id):
        return await ctx.send("🚫 Bạn chưa xác thực key. Dùng `.key <key>` trước.")

    if not md5 or len(md5) < 12:
        return await ctx.send("⚠️ Dùng đúng cú pháp: `.toolvip <md5>`")

    try:
        a = int(md5[0:4], 16) % 6 + 1
        b = int(md5[4:8], 16) % 6 + 1
        c = int(md5[8:12], 16) % 6 + 1
        dice = [a, b, c]
        total = sum(dice)
        prediction = "Tài" if total >= 11 else "Xỉu"
        confidence = "Cao" if 10 <= total <= 11 else "Trung bình"
        bias = "⚖️ Nghiêng về Tài" if total > 10 else "⚖️ Nghiêng về Xỉu"
        if total <= 6:
            prob = random.randint(50, 60)
        elif total <= 10:
            prob = random.randint(60, 70)
        else:
            prob = random.randint(70, 80)

        msg = (
            f"🎯 **Phân tích MD5:** `{md5}`\n"
            f"🎲 Xúc xắc: {dice}\n"
            f"🔢 Tổng điểm: **{total}**\n"
            f"💡 Dự đoán: **{prediction}**\n"
            f"📊 Độ tin cậy: **{confidence}**\n"
            f"{bias}\n"
            f"🎯 Xác suất đúng (ước lượng): ≈ {prob}%"
        )
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {e}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Bot đang hoạt động!")

# ------------------ KEEP ALIVE -----------------------
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"
def run():
    app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# ------------------ START BOT ------------------------
bot.run(os.getenv("DISCORD_TOKEN"))
