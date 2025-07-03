import discord from discord.ext import commands import hashlib import json import os import time from datetime import datetime, timedelta from flask import Flask from threading import Thread

intents = discord.Intents.default() intents.message_content = True bot = commands.Bot(command_prefix=".", intents=intents)

TOKEN = os.getenv("DISCORD_TOKEN") ADMIN_ID = 1115314183731421274  # Thay bằng ID admin thật của bạn KEY_FILE = "keys.json" LOG_FILE = "log.txt" COOLDOWN_SECONDS = 10 user_cooldowns = {}

Tạo web server đơn giản để uptime bot

app = Flask('')

@app.route('/') def home(): return "Bot is alive!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive(): t = Thread(target=run) t.start()

keep_alive()

def load_keys(): try: with open(KEY_FILE, 'r') as f: return json.load(f) except FileNotFoundError: return {}

def save_keys(keys): with open(KEY_FILE, 'w') as f: json.dump(keys, f, indent=4)

def is_key_valid(user_id, key): keys = load_keys() if key not in keys: return False, "Bạn đã nhập sai key. Vui lòng liên hệ admin để được hỗ trợ." if keys[key]["user"] != 0 and keys[key]["user"] != user_id: return False, "Key này đã được sử dụng bởi người khác." expiry = datetime.strptime(keys[key]["expiry"], "%Y-%m-%d") if expiry < datetime.now(): return False, "Key đã hết hạn." return True, ""

def use_key(user_id, key): keys = load_keys() keys[key]["user"] = user_id save_keys(keys)

def renew_key(key): keys = load_keys() if key in keys: new_expiry = datetime.now() + timedelta(days=30) keys[key]["expiry"] = new_expiry.strftime("%Y-%m-%d") save_keys(keys) return True return False

def get_key_info(user_id): keys = load_keys() for k, v in keys.items(): if v["user"] == user_id: expiry = datetime.strptime(v["expiry"], "%Y-%m-%d") days_left = (expiry - datetime.now()).days return k, days_left return None, None

def md5_predict(md5_hash): nums = [int(md5_hash[i], 16) for i in [0, 2, 4]] dice = [n % 6 + 1 for n in nums] total = sum(dice) result = "Tài" if total >= 11 else "Xỉu" confidence = "Cao" if total in range(10, 13) else "Trung bình" percent = {"Cao": "≈ 75%", "Trung bình": "≈ 65%"}[confidence] return dice, total, result, confidence, percent

@bot.command() async def toolvip(ctx, md5: str): user_id = str(ctx.author.id) now = time.time() if user_id in user_cooldowns and now - user_cooldowns[user_id] < COOLDOWN_SECONDS: await ctx.send("⏳ Bạn cần chờ trước khi dùng lại lệnh này.") return user_cooldowns[user_id] = now

keys = load_keys()
user_has_key = any(v["user"] == int(user_id) for v in keys.values())

if not user_has_key:
    await ctx.send(f"❌ Bạn đã nhập sai key. Vui lòng liên hệ admin để được hỗ trợ. <@{ADMIN_ID}>")
    return

dice, total, result, confidence, percent = md5_predict(md5)
await ctx.send(
    f"🎯 **Phân tích MD5:** `{md5}`\n🎲 Xúc xắc: {dice}\n🔢 Tổng điểm: {total}\n💡 Dự đoán: **{result}**\n📊 Độ tin cậy: **{confidence}**\n📌 Xác suất đúng (ước lượng): {percent}"
)

with open(LOG_FILE, 'a') as f:
    f.write(f"{ctx.author} | {md5} | {result}\n")

@bot.command() async def key(ctx, key: str): user_id = str(ctx.author.id) valid, message = is_key_valid(int(user_id), key) if not valid: await ctx.send(f"❌ {message} <@{ADMIN_ID}>") return

# Check nếu user đã dùng key khác
current_key, _ = get_key_info(int(user_id))
if current_key:
    await ctx.send("⚠️ Mỗi người chỉ được dùng 1 key duy nhất.")
    return

use_key(int(user_id), key)
await ctx.send("✅ Key đã được kích hoạt thành công!")

@bot.command() async def checkkey(ctx): user_id = str(ctx.author.id) key, days = get_key_info(int(user_id)) if key: await ctx.send(f"🔑 Key của bạn: {key}\n⏳ Còn hạn: {days} ngày") else: await ctx.send("❌ Bạn chưa dùng key nào hoặc key không hợp lệ.")

@bot.command() async def renewkey(ctx, key: str): if ctx.author.id != ADMIN_ID: await ctx.send("❌ Bạn không có quyền sử dụng lệnh này.") return if renew_key(key): await ctx.send("🔁 Đã gia hạn key thêm 30 ngày.") else: await ctx.send("❌ Key không tồn tại.")

bot.run(TOKEN)

