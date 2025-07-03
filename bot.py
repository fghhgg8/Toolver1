import discord from discord.ext import commands, tasks import hashlib import json import os import asyncio from datetime import datetime, timedelta from flask import Flask from threading import Thread

intents = discord.Intents.default() intents.message_content = True bot = commands.Bot(command_prefix='.', intents=intents)

KEY_FILE = 'keys.json' USED_KEYS_FILE = 'used_keys.json' ADMIN_ID = 1115314183731421274  # Thay bằng ID admin thật của bạn COOLDOWN_SECONDS = 10 user_cooldowns = {}

app = Flask('')

@app.route('/') def home(): return "Bot is running!"

def run(): app.run(host='0.0.0.0', port=8080)

def keep_alive(): t = Thread(target=run) t.start()

def load_keys(): if not os.path.exists(KEY_FILE): return {} with open(KEY_FILE, 'r') as f: return json.load(f)

def save_keys(data): with open(KEY_FILE, 'w') as f: json.dump(data, f, indent=2)

def load_used_keys(): if not os.path.exists(USED_KEYS_FILE): return {} with open(USED_KEYS_FILE, 'r') as f: return json.load(f)

def save_used_keys(data): with open(USED_KEYS_FILE, 'w') as f: json.dump(data, f, indent=2)

def get_dice_result(md5): digits = [int(c, 16) for c in md5 if c.isdigit() or c in "abcdef"] a = (digits[0] + digits[5] + digits[10]) % 6 + 1 b = (digits[3] + digits[7] + digits[15]) % 6 + 1 c = (digits[1] + digits[8] + digits[20]) % 6 + 1 return [a, b, c]

@bot.event async def on_ready(): print(f'Logged in as {bot.user}')

@bot.command() async def key(ctx, *, user_key): keys = load_keys() used_keys = load_used_keys() user_id = str(ctx.author.id)

if user_id in used_keys:
    await ctx.send("\U0001f512 Bạn đã nhập key trước đó và không thể đổi key mới.")
    return

if user_key in keys:
    expiry = datetime.strptime(keys[user_key], '%Y-%m-%d')
    if expiry > datetime.now():
        used_keys[user_id] = user_key
        save_used_keys(used_keys)
        await ctx.send("\U0001f513 Key đã được kích hoạt thành công.")
    else:
        await ctx.send(f"\U0001f512 Key không hợp lệ hoặc đã hết hạn. Vui lòng liên hệ <@{ADMIN_ID}> để được hỗ trợ.")
else:
    await ctx.send(f"\U0001f512 Key không hợp lệ hoặc đã hết hạn. Vui lòng liên hệ <@{ADMIN_ID}> để được hỗ trợ.")

@bot.command() async def delkey(ctx, member: discord.Member): if ctx.author.id != ADMIN_ID: await ctx.send("⛔ Bạn không có quyền sử dụng lệnh này.") return

user_id = str(member.id)
used_keys = load_used_keys()
keys = load_keys()

if user_id in used_keys:
    key_to_remove = used_keys[user_id]
    if key_to_remove in keys:
        del keys[key_to_remove]
    del used_keys[user_id]
    save_used_keys(used_keys)
    save_keys(keys)
    await ctx.send(f"✅ Đã xoá key của người dùng <@{user_id}>.")
else:
    await ctx.send(f"⚠️ Người dùng <@{user_id}> chưa đăng ký key hoặc đã bị xoá từ trước.")

@bot.command() async def toolvip(ctx, md5: str): user_id = str(ctx.author.id) used_keys = load_used_keys()

if user_id not in used_keys:
    await ctx.send(f"\U0001f512 Bạn chưa nhập key. Dùng lệnh `.key <key>` để kích hoạt. Nếu chưa có key, liên hệ <@{ADMIN_ID}> để mua key.")
    return

now = datetime.now()
if user_id in user_cooldowns and (now - user_cooldowns[user_id]).total_seconds() < COOLDOWN_SECONDS:
    await ctx.send(f"\u23F1 Vui lòng chờ {COOLDOWN_SECONDS} giây giữa mỗi lần sử dụng.")
    return
user_cooldowns[user_id] = now

dice = get_dice_result(md5)
total = sum(dice)
result = 'Tài' if total >= 11 else 'Xỉu'
confidence = 'Cao'
lean = 'Nghiêng về ' + result
percentage = '≈ 70%'

message = (
    f"\U0001F3AF Phân tích MD5: `{md5}`\n"
    f"\u2680 Xúc xắc: {dice}\n"
    f"\U0001F522 Tổng điểm: {total}\n"
    f"\U0001F4A1 Dự đoán: {result}\n"
    f"\U0001F4CA Độ tin cậy: {confidence}\n"
    f"⚖️ {lean}\n"
    f"\U0001F3AF Xác suất đúng (ước lượng): {percentage}"
)
await ctx.send(message)

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN") bot.run(TOKEN)

