from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

import requests
import sqlite3
import asyncio
import time
import shutil
import os
import logging

from datetime import datetime, timedelta

# =========================
# LOGGING
# =========================
logging.basicConfig(level=logging.INFO)

# =========================
# AUTO CREATE FOLDER
# =========================
os.makedirs("logs", exist_ok=True)
os.makedirs("exports", exist_ok=True)
os.makedirs("backups", exist_ok=True)

# =========================
# CONFIG
# =========================
TOKEN = os.getenv("8951314065:AAFzOPoPpJdL2aWqQyfyLgVNLbrq8sRdMeM")
API_KEY = os.getenv("d9e9eea76cc77356954de5ffbc40086a")

ADMINS = [5666003349]

# =========================
# DATABASE
# =========================
conn = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    limit_cek INTEGER DEFAULT 20,
    premium_expired TEXT,
    last_reset TEXT
)
""")

conn.commit()

# =========================
# COOLDOWN
# =========================
cooldown = {}

# =========================
# FUNCTIONS
# =========================
def is_admin(user_id):
    return user_id in ADMINS

def add_user(user_id, username):

    c.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    )

    data = c.fetchone()

    if not data:

        today = datetime.now().strftime("%Y-%m-%d")

        c.execute(
            """
            INSERT INTO users (
                user_id,
                username,
                last_reset
            )
            VALUES (?, ?, ?)
            """,
            (
                user_id,
                username,
                today
            )
        )

        conn.commit()

def is_premium(user_id):

    c.execute(
        """
        SELECT premium_expired
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    data = c.fetchone()

    if not data:
        return False

    if data[0] is None:
        return False

    expired = datetime.strptime(
        data[0],
        "%Y-%m-%d"
    )

    return expired >= datetime.now()

def get_limit(user_id):

    c.execute(
        """
        SELECT limit_cek
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    data = c.fetchone()

    if data:
        return data[0]

    return 0

def kurangi_limit(user_id):

    c.execute(
        """
        UPDATE users
        SET limit_cek = limit_cek - 1
        WHERE user_id=?
        """,
        (user_id,)
    )

    conn.commit()

def reset_limit(user_id):

    today = datetime.now().strftime("%Y-%m-%d")

    c.execute(
        """
        SELECT last_reset
        FROM users
        WHERE user_id=?
        """,
        (user_id,)
    )

    data = c.fetchone()

    if data:

        if data[0] != today:

            c.execute(
                """
                UPDATE users
                SET limit_cek=20,
                last_reset=?
                WHERE user_id=?
                """,
                (today, user_id)
            )

            conn.commit()

# =========================
# BACKUP DATABASE
# =========================
def backup_database():

    try:

        waktu = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        tujuan = f"backups/users_{waktu}.db"

        shutil.copy(
            "users.db",
            tujuan
        )

    except:
        pass

# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(user.id, user.username)

    keyboard = [
        [
            InlineKeyboardButton(
                "📱 CEK NOMOR",
                callback_data="cek"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ PREMIUM",
                callback_data="premium"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    teks = """
🔥 BOT CEK NOMOR PREMIUM 🔥

Kirim nomor dengan kode negara

Contoh:
+628123456789

Multi cek:
+628111111111
+628222222222
"""

    await update.message.reply_text(
        teks,
        reply_markup=reply_markup
    )

# =========================
# PROFILE
# =========================
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    limit_user = get_limit(user_id)

    premium = is_premium(user_id)

    status = "PREMIUM ⭐" if premium else "FREE 👤"

    teks = f"""
👤 ID: {user_id}

⭐ STATUS: {status}

📊 LIMIT HARIAN: {limit_user}
"""

    await update.message.reply_text(teks)

# =========================
# BUTTON
# =========================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "cek":

        await query.message.reply_text(
            "📥 Kirim nomor untuk dicek"
        )

    elif query.data == "premium":

        await query.message.reply_text(
            "⭐ Premium = Unlimited Check"
        )

# =========================
# CEK NOMOR
# =========================
async def cek_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    user_id = user.id

    add_user(user.id, user.username)

    # =========================
    # ANTI SPAM
    # =========================
    if user_id in cooldown:

        if time.time() - cooldown[user_id] < 10:

            await update.message.reply_text(
                "🚫 Jangan spam"
            )

            return

    cooldown[user_id] = time.time()

    # =========================
    # RESET LIMIT
    # =========================
    reset_limit(user_id)

    # =========================
    # LIMIT USER GRATIS
    # =========================
    if not is_premium(user_id):

        limit_user = get_limit(user_id)

        if limit_user <= 0:

            await update.message.reply_text(
                "❌ Limit harian habis"
            )

            return

    daftar_nomor = update.message.text.splitlines()

    # =========================
    # LIMIT MULTI CHECK
    # =========================
    if len(daftar_nomor) > 20:

        await update.message.reply_text(
            "❌ Maksimal 20 nomor"
        )

        return

    jumlah = len(daftar_nomor)

    loading = await update.message.reply_text(
        f"⏳ Sedang mengecek {jumlah} nomor..."
    )

    hasil_semua = ""

    for nomor in daftar_nomor:

        # VALIDASI NOMOR
        if not nomor.startswith("+"):
            continue

        url = f"http://apilayer.net/api/validate?access_key={API_KEY}&number={nomor}"

        try:

            response = requests.get(url)

            data = response.json()

            valid = data.get("valid")

            country = data.get("country_name")

            carrier = data.get("carrier")

            line_type = data.get("line_type")

            score = 0

            if line_type:

                if "voip" in line_type.lower():
                    score += 80

                elif "mobile" in line_type.lower():
                    score += 10

                else:
                    score += 40

            else:
                score += 50

            if score >= 70:
                status = "🔴 RISIKO TINGGI"

            elif score >= 40:
                status = "🟡 RISIKO SEDANG"

            else:
                status = "🟢 RISIKO RENDAH"

            hasil = f"""
📱 NOMOR: {nomor}

🌍 NEGARA: {country}

📡 OPERATOR: {carrier}

🧠 JENIS: {line_type}

{status}

📊 SCORE: {score}%
"""

            if valid:

                hasil += "\n✅ VALID"

                if line_type:

                    if "voip" in line_type.lower():
                        hasil += "\n☎️ VOIP / VIRTUAL"

                    else:
                        hasil += "\n📲 NOMOR NORMAL"

            else:

                hasil += "\n❌ NOMOR TIDAK VALID"

            hasil += "\n━━━━━━━━━━━━━━\n"

            hasil_semua += hasil

            # SAVE LOG
            with open(
                f"logs/{user_id}.txt",
                "a"
            ) as log:

                log.write(
                    f"{nomor} | {carrier} | {line_type}\n"
                )

        except:

            hasil_semua += "\n❌ Gagal cek nomor\n"

    # =========================
    # KURANGI LIMIT
    # =========================
    if not is_premium(user_id):

        kurangi_limit(user_id)

    # =========================
    # HAPUS LOADING
    # =========================
    try:
        await loading.delete()

    except:
        pass

    # =========================
    # KIRIM HASIL
    # =========================
    msg = await update.message.reply_text(
        hasil_semua
    )

    # =========================
    # EXPORT TXT PREMIUM
    # =========================
    if is_premium(user_id):

        with open(
            "exports/hasil.txt",
            "w"
        ) as f:

            f.write(hasil_semua)

        await update.message.reply_document(
            open(
                "exports/hasil.txt",
                "rb"
            )
        )

    # =========================
    # AUTO DELETE
    # =========================
    await asyncio.sleep(30)

    try:
        await msg.delete()

    except:
        pass

# =========================
# ADD PREMIUM
# =========================
async def addpremium(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    try:

        user_id = int(context.args[0])

        expired = datetime.now() + timedelta(days=1)

        c.execute(
            """
            UPDATE users
            SET premium_expired=?
            WHERE user_id=?
            """,
            (
                expired.strftime("%Y-%m-%d"),
                user_id
            )
        )

        conn.commit()

        await update.message.reply_text(
            "✅ Premium aktif 1 hari"
        )

    except:

        await update.message.reply_text(
            "Contoh:\n/addpremium 123456789"
        )

# =========================
# STATS
# =========================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    c.execute("SELECT COUNT(*) FROM users")

    total = c.fetchone()[0]

    teks = f"""
📊 STATISTIK BOT

👤 Total User: {total}
"""

    await update.message.reply_text(teks)

# =========================
# BACKUP
# =========================
async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    backup_database()

    await update.message.reply_text(
        "✅ Backup database berhasil"
    )

# =========================
# ERROR HANDLER
# =========================
async def error_handler(update, context):

    print(f"ERROR: {context.error}")

# =========================
# RUN BOT
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))

app.add_handler(CommandHandler("profile", profile))

app.add_handler(CommandHandler("stats", stats))

app.add_handler(CommandHandler("backup", backup))

app.add_handler(CommandHandler("addpremium", addpremium))

app.add_handler(
    CallbackQueryHandler(button)
)

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        cek_nomor
    )
)

app.add_error_handler(error_handler)

print("Bot berjalan...")

app.run_polling()
