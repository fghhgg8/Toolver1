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
async def danhsach(ctx):
    if ctx.author.id != ADMIN_ID:
        return
    entries = [log for log in MD5_LOG if log['user'] == str(ctx.author.id) and log['version'] == 'dts' and log['real_result']]
    if not entries:
        await ctx.send("📭 Bạn chưa có kết quả thật nào.")
        return
    msg = "📋 **Danh sách kết quả `.dts` đã lưu:**\n"
    for e in entries[-10:]:
        msg += f"• MD5: `{e['md5']}` → Bot: {e['bot_result']} | Thật: {e['real_result']}\n"
    await ctx.send(msg)

@bot.command()
async def danhsachv1(ctx):
    if ctx.author.id != ADMIN_ID:
        return
    entries = [log for log in MD5_LOG if log['user'] == str(ctx.author.id) and log['version'] == 'dtsv1' and log['real_result']]
    if not entries:
        await ctx.send("📭 Bạn chưa có kết quả thật nào.")
        return
    msg = "📋 **Danh sách kết quả `.dtsv1` đã lưu:**\n"
    for e in entries[-10:]:
        msg += f"• MD5: `{e['md5']}` → Bot: {e['bot_result']} | Thật: {e['real_result']}\n"
    await ctx.send(msg)

@bot.command()
async def lenh(ctx):
    if ctx.author.id != ADMIN_ID:
        return
    help_text = (
        "📘 **DANH SÁCH LỆNH HỖ TRỢ:**\n\n"
        "🔑 **Quản lý Key:**\n"
        "• `.key <key>` — Nhập key cho `.dts`\n"
        "• `.keyv1 <key>` — Nhập key cho `.dtsv1`\n"
        "• `.taokeydts <key> <số ngày>` — (Admin) Tạo key `.dts`\n"
        "• `.taokeydtsv1 <key> <số ngày>` — (Admin) Tạo key `.dtsv1`\n\n"
        "🎲 **Dự đoán:**\n"
        "• `.dts <md5>` — Dự đoán MD5 (thường)\n"
        "• `.dtsv1 <md5>` — Dự đoán MD5 (nâng cấp)\n\n"
        "📋 **Xem kết quả:**\n"
        "• `.danhsach` — Kết quả thật `.dts`\n"
        "• `.danhsachv1` — Kết quả thật `.dtsv1`\n\n"
        "🎨 **Quản lý màu:**\n"
        "• `.mau <user_id> <hex_color>` — Đổi màu tên user (Admin)"
    )
    await ctx.send(help_text)

@bot.command()
async def mau(ctx, user_id: int, color_hex: str):
    if ctx.author.id != ADMIN_ID:
        return
    guild = ctx.guild
    member = guild.get_member(user_id)
    if not member:
        await ctx.send("❌ Không tìm thấy user trong server.")
        return
    try:
        color_value = int(color_hex.lstrip("#"), 16)
        role_name = f"color_{user_id}"
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            role = await guild.create_role(name=role_name, color=discord.Color(color_value))
        else:
            await role.edit(color=discord.Color(color_value))
        await member.add_roles(role)
        await ctx.send(f"✅ Đã đổi màu tên cho <@{user_id}>.")
    except Exception as e:
        await ctx.send(f"❌ Lỗi: {str(e)}")

# FastAPI giữ bot online
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

bot.run(TOKEN)
