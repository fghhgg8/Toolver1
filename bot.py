""import discord from discord.ext import commands, tasks import hashlib import json import os import asyncio from datetime import datetime, timedelta

intents = discord.Intents.default() intents.message_content = True bot = commands.Bot(command_prefix='.', intents=intents)

ADMIN_IDS = [1115314183731421274]  # Thay bằng ID admin thật KEY_FILE = 'key_data.json' user_cooldowns = {}

=== Load key data ===

def load_keys(): try: with open(KEY_FILE, 'r') as f: return json.load(f) except: return {}

=== Save key data ===

def save_keys(keys): with open(KEY_FILE, 'w') as f: json.dump(keys, f, indent=4)

=== Hàm kiểm tra key ===

def is_key_valid(key_data, user_id): if key_data.get("user_id") not in ["", user_id]: return False, "🔒 Key này đã được sử dụng bởi người dùng khác." if datetime.strptime(key_data["expire"], "%Y-%m-%d") < datetime.now(): return False, "🔒 Key đã hết hạn." return True, ""

=== Phân tích MD5 (thuật toán mới) ===

def analyze_md5(md5): try: values = [int(md5[i], 16) for i in [-1, -2, -3]] dices = [v % 6 + 1 for v in values] total = sum(dices) result = "Tài" if total >= 11 else "Xỉu" return dices, total, result except: return [], 0, "Lỗi"

=== Lệnh nhập key ===

@bot.command() async def key(ctx, key): keys = load_keys() user_id = str(ctx.author.id) # Kiểm tra nếu user đã dùng key if any(data.get("user_id") == user_id for data in keys.values()): await ctx.send("🔐 Bạn đã nhập key trước đó và không thể đổi key mới.") return if key not in keys: await ctx.send(f"🔒 Key không hợp lệ hoặc đã hết hạn.\n📩 Vui lòng liên hệ <@{ADMIN_IDS[0]}> để được hỗ trợ.") return valid, msg = is_key_valid(keys[key], user_id) if not valid: await ctx.send(f"{msg}\n📩 Vui lòng liên hệ <@{ADMIN_IDS[0]}> để được hỗ trợ.") return keys[key]["user_id"] = user_id save_keys(keys) await ctx.send("✅ Key hợp lệ. Bạn có thể sử dụng lệnh .toolvip")

=== Lệnh dùng toolvip ===

@bot.command() async def toolvip(ctx, md5): user_id = str(ctx.author.id) keys = load_keys() if not any(data.get("user_id") == user_id for data in keys.values()): await ctx.send("🔑 Bạn chưa nhập key hợp lệ. Dùng .key <key> trước.") return

# Giới hạn 10s mỗi lần dùng
now = datetime.now()
if user_id in user_cooldowns and (now - user_cooldowns[user_id]).total_seconds() < 10:
    await ctx.send("⏳ Bạn chỉ được dùng lệnh này mỗi 10 giây.")
    return
user_cooldowns[user_id] = now

dices, total, result = analyze_md5(md5)
await ctx.send(
    f"🎯 Phân tích MD5: `{md5}`\n🎲 Xúc xắc: {dices}\n🔢 Tổng điểm: {total}\n💡 Dự đoán: {result}"
)

=== Check hạn key ===

@bot.command() async def checkkey(ctx): user_id = str(ctx.author.id) keys = load_keys() for k, v in keys.items(): if v.get("user_id") == user_id: expire = v["expire"] await ctx.send(f"🔑 Key của bạn: {k}\n⏳ Hạn sử dụng đến: {expire}") return await ctx.send("❌ Bạn chưa nhập key hoặc key không hợp lệ.")

=== Admin: gia hạn key ===

@bot.command() async def renewkey(ctx, key): if ctx.author.id not in ADMIN_IDS: return keys = load_keys() if key in keys: new_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d") keys[key]["expire"] = new_date save_keys(keys) await ctx.send(f"✅ Đã gia hạn key {key} đến {new_date}.") else: await ctx.send("❌ Key không tồn tại.")

=== Admin: xóa toàn bộ liên kết key ===

@bot.command() async def delkey(ctx): if ctx.author.id not in ADMIN_IDS: return keys = load_keys() for key in keys: keys[key]["user_id"] = "" save_keys(keys) await ctx.send("🧹 Đã xóa toàn bộ liên kết user-key.")

=== Ping UptimeRobot ===

@bot.event async def on_ready(): print(f'Bot đã đăng nhập: {bot.user}') ping_uptime.start()

@tasks.loop(minutes=5) async def ping_uptime(): try: import requests requests.get("https://your-uptime-link") except: pass

=== Chạy bot ===

import threading from keep_alive import keep_alive

keep_alive()  # Giữ bot sống bot.run(os.getenv("DISCORD_TOKEN"))

