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

@bot.command()
async def taokeydtsv1(ctx, key: str, days: int):
    if ctx.author.id != ADMIN_ID:
        return
    expire_date = (datetime.utcnow() + timedelta(days=days)).strftime('%Y-%m-%d')
    KEYS_DB[key] = {"expire": expire_date, "type": "dtsv1"}
    save_all()
    await ctx.send(f"✅ Đã tạo key `{key}` cho `.dtsv1`, hết hạn vào {expire_date}")

@bot.command()
async def dtsv1(ctx, md5: str):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()
    if user_id not in USER_KEYS or "dtsv1" not in USER_KEYS[user_id]:
        await ctx.send(f"❌ Bạn chưa nhập key. Dùng `.keyv1 <key>` trước. <@{ADMIN_ID}>")
        return

    keys = USER_KEYS[user_id]["dtsv1"]
    if isinstance(keys, str):
        keys = [keys]

    valid = False
    for key in keys:
        if key in KEYS_DB and datetime.strptime(KEYS_DB[key]['expire'], '%Y-%m-%d') >= now:
            valid = True
            break

    if not valid:
        del USER_KEYS[user_id]["dtsv1"]
        save_all()
        await ctx.send(f"❌ Key đã hết hạn. Liên hệ admin <@{ADMIN_ID}>")
        return

    result = predict_dice_v1(md5)
    if not result:
        await ctx.send("❌ MD5 không hợp lệ.")
        return

    MD5_LOG.append({
        "user": user_id,
        "md5": md5,
        "bot_result": result['xúc_xắc'],
        "real_result": None,
        "version": "dtsv1"
    })
    save_all()

    msg = (
        f"🎲 [DTSV1] Kết quả dự đoán:\n"
        f"• Xúc xắc: {result['xúc_xắc']}\n"
        f"• Tổng: {result['tổng']} ({result['kết_quả']})\n"
        f"• Độ tin cậy: {result['độ_tin_cậy']}\n\n"
        f"✨ DTS TOOL VIP – MUỐN MUA KEY LIÊN HỆ ADMIN <@{ADMIN_ID}>"
    )
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
        "• `.taokeydts <key> <số ngày>`\n"
        "• `.taokeydtsv1 <key> <số ngày>`\n\n"
        "🎲 **Dự đoán:**\n"
        "• `.dts <md5>`\n"
        "• `.dtsv1 <md5>`\n"
        "📋 `.danhsach` `.danhsachv1`\n"
        "🎨 `.mau <user_id> <hex_color>`"
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

# FastAPI server giữ bot online
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

bot.run(TOKEN)
