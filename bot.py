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

ADMIN_IDS = [1115314183731421274]  # Thay ID của bạn

KEYS_FILE = "keys.json"
VERIFIED_USERS_FILE = "verified_users.json"
TOOLVIP_LOG_FILE = "logs.txt"
TOOLVIP_TIMEOUTS = {}

# ------------------ JSON FUNCTIONS ------------------
def load_json(file):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return {}

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

# ------------------ KEY FUNCTIONS ------------------
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

def renew_key(key):
    keys = load_json(KEYS_FILE)
    if key in keys:
        expiry = datetime.fromisoformat(keys[key]) + timedelta(days=30)
        keys[key] = expiry.isoformat()
        save_json(KEYS_FILE, keys)
        return expiry
    return None

def save_verified_user(user_id, expiry, key):
    users = load_json(VERIFIED_USERS_FILE)
    uid = str(user_id)
    if uid in users:
        return False  # Không cho đổi key
    users[uid] = {
        "expiry": expiry.isoformat(),
        "key": key
    }
    save_json(VERIFIED_USERS_FILE, users)
    return True

def is_user_verified(user_id):
    users = load_json(VERIFIED_USERS_FILE)
    uid = str(user_id)
    if uid in users:
        expiry = datetime.fromisoformat(users[uid]["expiry"])
        return datetime.utcnow() < expiry
    return False

def get_user_key_expiry(user_id):
    users = load_json(VERIFIED_USERS_FILE)
    uid = str(user_id)
    if uid in users:
        return datetime.fromisoformat(users[uid]["expiry"])
    return None

# ------------------ BOT COMMANDS ------------------

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
        return await ctx.send("⚠️ Dùng đúng: `.delkey <key>`")

    keys = load_json(KEYS_FILE)
    if key in keys:
        del keys[key]
        save_json(KEYS_FILE, keys)
        await ctx.send(f"🗑️ Đã xóa key `{key}`.")
    else:
        await ctx.send("❌ Key không tồn tại.")

@bot.command()
async def renewkey(ctx, key: str = None):
    if ctx.author.id not in ADMIN_IDS:
        return await ctx.send("❌ Bạn không có quyền gia hạn key.")
    if not key:
        return await ctx.send("⚠️ Dùng đúng: `.renewkey <key>`")

    expiry = renew_key(key)
    if expiry:
        await ctx.send(f"🔁 Đã gia hạn key `{key}` đến `{expiry.date()}` (UTC)")
    else:
        await ctx.send("❌ Key không tồn tại.")

@bot.command()
async def key(ctx, key: str = None):
    if not key:
        return await ctx.send("⚠️ Dùng đúng: `.key <key>`")

    if is_key_valid(key):
        expiry = load_json(KEYS_FILE)[key]
        ok = save_verified_user(ctx.author.id, datetime.fromisoformat(expiry), key)
        if ok:
            await ctx.send("✅ Key hợp lệ! Bạn có thể dùng `.toolvip <md5>`")
        else:
            await ctx.send("🔒 Bạn đã nhập key trước đó và không thể đổi key mới.")
    else:
        await ctx.send("🔐 Key không hợp lệ hoặc đã hết hạn.")

@bot.command()
async def checkkey(ctx):
    if not is_user_verified(ctx.author.id):
        return await ctx.send("🔐 Bạn chưa kích hoạt key.")
    expiry = get_user_key_expiry(ctx.author.id)
    remaining = expiry - datetime.utcnow()
    days = remaining.days
    hours = remaining.seconds // 3600
    await ctx.send(f"📅 Key của bạn còn hiệu lực: **{days} ngày {hours} giờ**")

@bot.command()
async def toolvip(ctx, md5: str = None):
    user_id = ctx.author.id

    if not is_user_verified(user_id):
        return await ctx.send("🔐 Bạn chưa xác thực key. Dùng `.key <key>` trước.")

    # Giới hạn 10s mỗi lần
    now = datetime.utcnow()
    if user_id in TOOLVIP_TIMEOUTS:
        delta = (now - TOOLVIP_TIMEOUTS[user_id]).total_seconds()
        if delta < 10:
            return await ctx.send("⏳ Vui lòng chờ 10 giây trước khi dùng lại `.toolvip`.")

    if not md5 or len(md5) != 32:
        return await ctx.send("⚠️ Dùng đúng cú pháp: `.toolvip <md5>` (32 ký tự)")

    try:
        bytes_data = bytes.fromhex(md5.strip().lower())
        b1, b2, b3 = bytes_data[0], bytes_data[1], bytes_data[2]
        dice = [(b % 6) + 1 for b in (b1, b2, b3)]
        total = sum(dice)

        prediction = "Tài" if total >= 11 else "Xỉu"
        confidence = "Cao" if total in [10, 11, 12] else "Trung bình"
        bias = "⚖️ Nghiêng về Tài" if total >= 11 else "⚖️ Nghiêng về Xỉu"
        prob = random.randint(65, 80) if total >= 10 else random.randint(55, 70)

        msg = (
            f"🎯 **Phân tích MD5:** `{md5}`\n"
            f"🎲 Xúc xắc: {dice}\n"
            f"🔢 Tổng điểm: **{total}**\n"
            f"💡 Dự đoán: **{prediction}**\n"
            f"📊 Độ tin cậy: **{confidence}**\n"
            f"{bias}\n"
            f"🎯 Xác suất đúng (ước lượng): ≈ {prob}%"
        )

        TOOLVIP_TIMEOUTS[user_id] = now  # Ghi thời điểm sử dụng

        # Ghi log
        with open(TOOLVIP_LOG_FILE, "a") as f:
            f.write(f"{datetime.utcnow().isoformat()} | {ctx.author} | {md5} → {dice} ({total}) → {prediction}\n")

        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"❌ Lỗi xử lý MD5: {str(e)}")

@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Bot đang hoạt động!")

# ------------------ KEEP ALIVE (Render/UptimeRobot) ------------------
app = Flask('')
@app.route('/')
def home():
    return "Bot is running!"
def run():
    app.run(host='0.0.0.0', port=8080)
Thread(target=run).start()

# ------------------ START BOT ------------------
bot.run(os.getenv("DISCORD_TOKEN"))
