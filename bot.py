import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json, os, hashlib
from fastapi import FastAPI
import uvicorn
import threading

# Lấy token từ biến môi trường DISCORD_TOKEN (Render dùng cái này)
TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID = 1115314183731421274
PREFIX = '.'

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents)

KEY_FILE = 'keys.json'
USER_KEYS = {}

# Tải key từ file nếu có
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, 'r') as f:
        USER_KEYS = json.load(f)

# Lưu key
def save_keys():
    with open(KEY_FILE, 'w') as f:
        json.dump(USER_KEYS, f, indent=4)

# Tự động xóa key hết hạn
def remove_expired_keys():
    now = datetime.utcnow()
    to_delete = [uid for uid, data in USER_KEYS.items() if datetime.strptime(data['expire'], '%Y-%m-%d') < now]
    for uid in to_delete:
        del USER_KEYS[uid]
    if to_delete:
        save_keys()

# Thuật toán đoán kết quả từ MD5
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

# Nhập key (1 lần duy nhất)
@bot.command()
async def key(ctx, key):
    user_id = str(ctx.author.id)
    remove_expired_keys()

    if user_id in USER_KEYS:
        await ctx.send("✅ Bạn đã nhập key và được xác nhận rồi.")
        return

    for k, v in USER_KEYS.items():
        if k != user_id and v['key'] == key:
            await ctx.send("❌ Key đã được sử dụng. Nếu share key sẽ bị ban và không hoàn phí 😡😡🤬")
            return

    for k, v in USER_KEYS.items():
        if v['key'] == key:
            expire = datetime.strptime(v['expire'], '%Y-%m-%d')
            if datetime.utcnow() > expire:
                await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
                return
            USER_KEYS[user_id] = {'key': key, 'expire': v['expire']}
            save_keys()
            await ctx.send("✅ Key xác nhận thành công. Bạn có thể dùng lệnh .dts <md5>")
            return

    await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")

# Tạo key với tên và số ngày sử dụng (chỉ admin)
@bot.command()
async def taokey(ctx, ten: str, songay: int):
    if ctx.author.id != ADMIN_ID:
        return
    key = ten.lower()
    expire_date = (datetime.utcnow() + timedelta(days=songay)).strftime('%Y-%m-%d')
    USER_KEYS[key] = {'key': key, 'expire': expire_date}
    save_keys()
    await ctx.send(f"✨ Key `{key}` được tạo, hết hạn vào: {expire_date}")

# Xoá key của người dùng hiện tại
@bot.command()
async def delkey(ctx):
    user_id = str(ctx.author.id)
    if user_id in USER_KEYS:
        del USER_KEYS[user_id]
        save_keys()
        await ctx.send("✅ Key của bạn đã được xóa. Bạn cần nhập lại key để sử dụng tiếp.")
    else:
        await ctx.send("⚠️ Bạn chưa nhập key nào trước đó.")

# Dự đoán kết quả từ MD5
@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dts(ctx, md5):
    user_id = str(ctx.author.id)
    remove_expired_keys()

    if user_id not in USER_KEYS:
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

# FastAPI để giữ bot online với UptimeRobot
app = FastAPI()

@app.get("/")
def root():
    return {"message": "Bot is alive!"}

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Khởi động server FastAPI trong luồng phụ
threading.Thread(target=run_web).start()

# Khởi động bot Discord
if __name__ == '__main__':
    bot.run(TOKEN)
