import discord from discord.ext import commands from datetime import datetime, timedelta import json, os from fastapi import FastAPI import uvicorn import threading

Sử dụng token từ biến môi trường

TOKEN = os.getenv("DISCORD_TOKEN") ADMIN_ID = 1115314183731421274 PREFIX = '.'

intents = discord.Intents.default() intents.message_content = True bot = commands.Bot(command_prefix=PREFIX, intents=intents)

KEY_FILE = 'keys.json' USER_KEYS = {}

if os.path.exists(KEY_FILE): with open(KEY_FILE, 'r') as f: USER_KEYS = json.load(f)

def save_keys(): with open(KEY_FILE, 'w') as f: json.dump(USER_KEYS, f, indent=4)

Thuật toán dự đoán mới

def predict_dice_from_md5(md5_hash: str): if len(md5_hash) != 32: return None try: bytes_array = [int(md5_hash[i:i+2], 16) for i in range(0, 32, 2)] dice1 = (bytes_array[2] ^ bytes_array[13]) % 6 + 1 dice2 = (bytes_array[4] + bytes_array[10]) % 6 + 1 dice3 = (bytes_array[6] ^ bytes_array[15]) % 6 + 1 total = dice1 + dice2 + dice3 result = 'Tài' if total >= 11 else 'Xỉu' trust = 'Thấp' if total in [10, 11]: trust = 'Cao' elif 9 <= total <= 12: trust = 'Trung bình' return { 'xúc_xắc': [dice1, dice2, dice3], 'tổng': total, 'kết_quả': result, 'độ_tin_cậy': trust } except: return None

@bot.command() async def key(ctx, key): user_id = str(ctx.author.id) now = datetime.utcnow()

# Cho admin nhập nhiều key
if ctx.author.id == ADMIN_ID:
    for v in USER_KEYS.values():
        if v['key'] == key:
            expire = datetime.strptime(v['expire'], '%Y-%m-%d')
            if now > expire:
                await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
                return
            USER_KEYS[user_id] = {'key': key, 'expire': v['expire']}
            save_keys()
            await ctx.send("✅ Key xác nhận thành công. Bạn có thể dùng lệnh .dts <md5>")
            return
    await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
    return

# Người thường chỉ 1 key
if user_id in USER_KEYS:
    await ctx.send("✅ Bạn đã nhập key và được xác nhận rồi.")
    return

for k, v in USER_KEYS.items():
    if k != user_id and v['key'] == key:
        await ctx.send(f"❌ Key đã được người khác sử dụng. Hãy dùng key khác hoặc liên hệ admin <@{ADMIN_ID}>.")
        return

for v in USER_KEYS.values():
    if v['key'] == key:
        expire = datetime.strptime(v['expire'], '%Y-%m-%d')
        if now > expire:
            await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")
            return
        USER_KEYS[user_id] = {'key': key, 'expire': v['expire']}
        save_keys()
        await ctx.send("✅ Key xác nhận thành công. Bạn có thể dùng lệnh .dts <md5>")
        return

await ctx.send(f"❌ Key không tồn tại vui lòng liên hệ admin để được cung cấp <@{ADMIN_ID}>")

@bot.command() async def delkey(ctx): user_id = str(ctx.author.id) if user_id in USER_KEYS: del USER_KEYS[user_id] save_keys() await ctx.send("✅ Key của bạn đã được xóa. Bạn cần nhập lại key để sử dụng tiếp.") else: await ctx.send("⚠️ Bạn chưa nhập key nào trước đó.")

@bot.command() @commands.cooldown(1, 10, commands.BucketType.user) async def dts(ctx, md5): user_id = str(ctx.author.id) now = datetime.utcnow()

if user_id not in USER_KEYS:
    await ctx.send(f"❌ Bạn chưa nhập key. Dùng lệnh `.key <key>` trước. Liên hệ admin <@{ADMIN_ID}>")
    return

expire = datetime.strptime(USER_KEYS[user_id]['expire'], '%Y-%m-%d')
if now > expire:
    del USER_KEYS[user_id]
    save_keys()
    await ctx.send(f"❌ Key đã hết hạn. Vui lòng liên hệ admin để được cung cấp key mới <@{ADMIN_ID}>")
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

Admin tạo key theo .taokey <tên> <số_ngày>

@bot.command() async def taokey(ctx, ten: str, songay: int): if ctx.author.id != ADMIN_ID: return key = ten.lower() expire_date = (datetime.utcnow() + timedelta(days=songay)).strftime('%Y-%m-%d') USER_KEYS[key] = {'key': key, 'expire': expire_date} save_keys() await ctx.send(f"✨ Key {key} tạo thành công, hết hạn ngày {expire_date}")

UptimeRobot server

app = FastAPI()

@app.get("/") def read_root(): return {"message": "Bot is alive!"}

def run_web(): uvicorn.run(app, host="0.0.0.0", port=8000)

threading.Thread(target=run_web).start()

bot.run(TOKEN)

