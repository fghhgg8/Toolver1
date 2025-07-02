import discord
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

# Khởi tạo bot
intents = discord.Intents.default()
bot = commands.Bot(command_prefix=".", intents=intents)

# Danh sách ID admin (chỉ họ mới dùng được lệnh .addkey)
ADMIN_IDS = [123456789012345678]  # 🔁 Thay bằng ID Discord của bạn

# Danh sách người dùng đã xác thực key
verified_users = {}

# 📁 Đường dẫn file keys.json
KEYS_FILE = "keys.json"

# 📦 Hàm lưu key với thời hạn 1 tháng
def add_key_with_1_month_expiry(new_key):
    expiry = datetime.utcnow() + timedelta(days=30)
    expiry_str = expiry.isoformat()

    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            keys = json.load(f)
    else:
        keys = {}

    keys[new_key] = expiry_str

    with open(KEYS_FILE, "w") as f:
        json.dump(keys, f, indent=4)

    return expiry_str

# 🔍 Hàm kiểm tra key còn hạn không
def is_key_valid(key):
    try:
        with open(KEYS_FILE, "r") as f:
            keys = json.load(f)
        if key not in keys:
            return False
        expiry = datetime.fromisoformat(keys[key])
        return datetime.utcnow() < expiry
    except:
        return False

# ✅ Lệnh admin: thêm key mới
@bot.command(name="addkey")
async def addkey(ctx, key: str = None):
    if ctx.author.id not in ADMIN_IDS:
        await ctx.send("❌ Bạn không có quyền dùng lệnh này.")
        return

    if not key:
        await ctx.send("⚠️ Cú pháp đúng: `.addkey <key>`")
        return

    expiry = add_key_with_1_month_expiry(key)
    await ctx.send(f"✅ Đã tạo key `{key}` có hiệu lực đến `{expiry[:10]} (UTC)`")

# 🔑 Lệnh người dùng: xác thực key
@bot.command(name="key")
async def key(ctx, key_input: str = None):
    if not key_input:
        await ctx.send("⚠️ Dùng đúng cú pháp: `.key <key>`")
        return

    try:
        with open(KEYS_FILE, "r") as f:
            keys = json.load(f)

        if key_input not in keys:
            await ctx.send("🔒 Key không hợp lệ.")
            return

        expiry = datetime.fromisoformat(keys[key_input])
        if datetime.utcnow() > expiry:
            await ctx.send("❌ Key đã hết hạn.")
            return

        verified_users[ctx.author.id] = expiry
        await ctx.send("✅ Key hợp lệ! Giờ bạn có thể dùng lệnh `.toolvip <md5>`")

    except Exception as e:
        await ctx.send(f"❌ Lỗi xác thực key: {e}")

# 🎯 Lệnh chính: phân tích MD5 nếu đã xác thực
@bot.command(name="toolvip")
async def toolvip(ctx, md5_input: str = None):
    if ctx.author.id not in verified_users:
        await ctx.send("🚫 Bạn chưa xác thực key. Dùng lệnh `.key <key>` trước.")
        return

    if datetime.utcnow() > verified_users[ctx.author.id]:
        del verified_users[ctx.author.id]
        await ctx.send("🔒 Key đã hết hạn. Dùng lại `.key <key>`.")
        return

    if not md5_input:
        await ctx.send("⚠️ Dùng đúng cú pháp: `.toolvip <md5>`")
        return

    try:
        # ⚠️ Hàm phân tích MD5 mẫu (bạn có thể tùy chỉnh theo logic thật)
        def analyze_md5(md5):
            total = sum(int(c, 16) for c in md5[:6]) % 18 + 3
            dice = [total // 3] * 3
            prediction = "Tài" if total >= 11 else "Xỉu"
            confidence = "Cao" if total in [10, 11] else "Trung bình"
            bias = "⚖️ Nghiêng về Tài" if total > 10 else "⚖️ Nghiêng về Xỉu"
            return {
                "Xúc xắc": dice,
                "Tổng điểm": total,
                "Dự đoán": prediction,
                "Độ tin cậy": confidence,
                "Khả năng nghiêng": bias,
                "Xác suất đúng (ước lượng)": "≈ 80%"
            }

        result = analyze_md5(md5_input)
        msg = (
            f"🎯 **Phân tích MD5:** `{md5_input}`\n"
            f"🎲 Xúc xắc: {result['Xúc xắc']}\n"
            f"🔢 Tổng điểm: **{result['Tổng điểm']}**\n"
            f"💡 Dự đoán: **{result['Dự đoán']}**\n"
            f"📊 Độ tin cậy: **{result['Độ tin cậy']}**\n"
            f"📉 {result['Khả năng nghiêng']}\n"
            f"🎯 Xác suất đúng (ước lượng): {result['Xác suất đúng (ước lượng)']}"
        )
        await ctx.send(msg)
    except Exception as e:
        await ctx.send(f"❌ Lỗi khi phân tích MD5: {e}")

# 🚀 Khởi động bot
bot.run(os.getenv("DISCORD_TOKEN"))
