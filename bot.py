import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json, os, hashlib
from fastapi import FastAPI
import uvicorn
import threading

# === Cấu hình cơ bản ===
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID = 1115314183731421274
PREFIX = '.'
KEY_FILE = 'keys.json'
USER_KEYS = {}  # {user_id: {"key": ..., "expire": ...}}

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

# === Tải và lưu file key ===
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'r') as f:
        USER_KEYS = json.load(f)

def save_keys():
    with open(KEY_FILE, 'w') as f:
        json.dump(USER_KEYS, f, indent=4)

# === Tự động xóa key hết hạn ===
@bot.event
async def on_ready():
    now = datetime.utcnow()
    expired_users = [uid for uid, data in USER_KEYS.items() if datetime.strptime(data['expire'], "%Y-%m-%d") < now]
    for uid in expired_users:
        del USER_KEYS[uid]
    save_keys()
    print(f"✅ Bot đã sẵn sàng với {len(USER_KEYS)} key hợp lệ.")

# === Thuật toán dự đoán MD5 ===
def predict_dice_from_md5(md5_hash: str):
    if len(md5_hash) != 32:
        return None
    try:
        bytes_array = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)]
        dice1 = (bytes_array[3] + bytes_array[10]) % 6 + 1
        dice2 = (bytes_array[5] + bytes_array[12]) % 6 + 1
        dice3 = (bytes_array[7] + bytes_array[14]) % 6 + 1
        total = dice1 + dice2 + dice3
        result = 'Tài' if total >= 11 else 'Xỉu'
        trust = 'Thấp'
        if total in [10, 11]:
            trust = 'Cao'
        elif 9 <= total <= 12:
            trust = 'Trung bình'
        return {
            'xúc_xắc': [dice1, dice2, dice3],
            'tổng': total,
            'kết_quả': result,
            'độ_tin_cậy': trust
        }
    except:
        return None

# === Nhập key ===
@bot.command()
async def key(ctx, key):
    user_id = str(ctx.author.id)
    now = datetime.utcnow()

    # Admin có thể dùng nhiều key
    if ctx.author.id == ADMIN_ID:
        for data in USER_KEYS.values():
            if data['key'] == key:
                expire = datetime.strptime(data['expire'], "%Y-%m-%d")
                if now > expire:
                    await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
                    return
                await ctx.send("✅ Admin xác nhận key thành công.")
                return

        await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
        return

    # Người thường: chỉ dùng 1 key duy nhất
    if user_id in USER_KEYS:
        await ctx.send("✅ Bạn đã nhập key và được xác nhận rồi.")
        return

    for uid, data in USER_KEYS.items():
        if uid != user_id and data['key'] == key:
            await ctx.send("❌ Key đã được người khác sử dụng. Hãy dùng key khác hoặc liên hệ admin.")
            return

    for data in USER_KEYS.values():
        if data['key'] == key:
            expire = datetime.strptime(data['expire'], "%Y-%m-%d")
            if now > expire:
                await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
                return
            USER_KEYS[user_id] = {'key': key, 'expire': data['expire']}
            save_keys()
            await ctx.send("✅ Key xác nhận thành công. Bạn có thể dùng lệnh `.dts <md5>`")
            return

    await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")

# === Xóa key người dùng ===
@bot.command()
async def delkey(ctx):
    if ctx.author.id != ADMIN_ID:
        user_id = str(ctx.author.id)
        if user_id in USER_KEYS:
            del USER_KEYS[user_id]
            save_keys()
            await ctx.send("✅ Key của bạn đã được xóa. Bạn cần nhập lại key để sử dụng tiếp.")
        else:
            await ctx.send("⚠️ Bạn chưa nhập key nào trước đó.")
    else:
        await ctx.send("❌ Admin không cần dùng lệnh này.")

# === Dự đoán MD5 ===
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dts(ctx, md5):
    user_id = str(ctx.author.id)
    if ctx.author.id != ADMIN_ID and user_id not in USER_KEYS:
        await ctx.send(f"❌ Bạn chưa nhập key. Dùng lệnh `.key <key>` trước. Liên hệ admin <@{ADMIN_ID}>")
        return

    result = predict_dice_from_md5(md5)
    if not result:
        await ctx.send("❌ MD5 không hợp lệ. Vui lòng nhập đúng 32 ký tự hex.")
        return

    msg = (
        f"🎲 Kết quả dự đoán từ MD5:\n"
        f"• Xúc xắc: {result['xúc_xắc']}\n"
        f"• Tổng: {result['tổng']} ({result['kết_quả']})\n"
        f"• Độ tin cậy: {result['độ_tin_cậy']}\n\n"
        f"✨ DTS TOOL VIP – MUỐN MUA KEY LIÊN HỆ ADMIN <@{ADMIN_ID}>"
    )
    await ctx.send(msg)

# === Tạo key (chỉ admin) ===
@bot.command()
async def taokey(ctx, ten: str, songay: int):
    if ctx.author.id != ADMIN_ID:
        return
    key = ten
    expire_date = (datetime.utcnow() + timedelta(days=songay)).strftime('%Y-%m-%d')
    USER_KEYS[key] = {"key": key, "expire": expire_date}
    save_keys()
    await ctx.send(f"🔑 Key mới: `{key}`\n📅 Hạn dùng: {expire_date}")

# === FastAPI server cho UptimeRobot ===
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

# === Chạy bot ===
if __name__ == "__main__":
    bot.run(TOKEN)
