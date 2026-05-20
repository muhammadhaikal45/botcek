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
import os

from datetime import datetime, timedelta

# =========================
# CONFIG
# =========================

TOKEN = "8752615272:AAGS7COBor0kpMrcHX_LPZoUYImEJwuFiU4"
API_KEY = "d9e9eea76cc77356954de5ffbc40086a"

ADMINS = [5666003349]

# =========================
# DATABASE
# =========================

conn = sqlite3.connect(
    "users.db",
    check_same_thread=False
)

c = conn.cursor()

c.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    limit_cek INTEGER DEFAULT 20,
    premium_expired TEXT,
    last_reset TEXT
)
''')

conn.commit()

# =========================
# ANTI SPAM
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

    cek = c.fetchone()

    if not cek:

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
# MENU
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    add_user(user.id, user.username)

    keyboard = [
        [
            InlineKeyboardButton(
                "CEK NOMOR",
                callback_data="cek"
            )
        ],
        [
            InlineKeyboardButton(
                "STATUS PREMIUM",
                callback_data="premium"
            )
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    teks = """
BOT CEK NOMOR PREMIUM

Kirim nomor dengan kode negara
"""

    await update.message.reply_text(
        teks,
        reply_markup=reply_markup
    )

# =========================
# BUTTON
# =========================

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    if query.data == "cek":

        await query.message.reply_text(
            "Kirim nomor untuk dicek"
        )

    elif query.data == "premium":

        await query.message.reply_text(
            "Premium aktif = unlimited cek"
        )

# =========================
# CEK NOMOR
# =========================

async def cek_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    user_id = user.id

    add_user(user.id, user.username)

    if user_id in cooldown:

        if time.time() - cooldown[user_id] < 5:

            await update.message.reply_text(
                "Jangan spam"
            )

            return

    cooldown[user_id] = time.time()

    reset_limit(user_id)

    if not is_premium(user_id):

        limit_user = get_limit(user_id)

        if limit_user <= 0:

            await update.message.reply_text(
                "Limit harian habis"
            )

            return

    daftar_nomor = update.message.text.splitlines()

    hasil_semua = ""

    for nomor in daftar_nomor:

        url = f"http://apilayer.net/api/validate?access_key={API_KEY}&number={nomor}"

        try:

            response = requests.get(url)

            data = response.json()

            valid = data.get("valid")

            country = data.get("country_name")

            carrier = data.get("carrier")

            line_type = data.get("line_type")

            hasil = f"""
HASIL CEK

Nomor: {nomor}
Negara: {country}
Operator: {carrier}
Jenis: {line_type}
"""

            if valid:

                hasil += "\nValid: YA"

                if line_type:

                    if "voip" in line_type.lower():

                        hasil += "\nStatus: VOIP / VIRTUAL"

                    else:

                        hasil += "\nStatus: NORMAL"

            else:

                hasil += "\nNomor tidak valid"

            hasil += "\n------------------\n"

            hasil_semua += hasil

            with open(
                f"logs/{user_id}.txt",
                "a"
            ) as log:

                log.write(
                    f"{nomor} | {carrier} | {line_type}\n"
                )

        except Exception as e:

            hasil_semua += f"\nError: {e}\n"

    if not is_premium(user_id):

        kurangi_limit(user_id)

    msg = await update.message.reply_text(
        hasil_semua
    )

    # EXPORT TXT PREMIUM

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

    await asyncio.sleep(30)

    try:
        await msg.delete()
    except:
        pass

# =========================
# PREMIUM
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
            "Premium aktif 1 hari"
        )

    except:

        await update.message.reply_text(
            "/addpremium ID"
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
STATISTIK BOT

Total User: {total}
"""

    await update.message.reply_text(teks)

# =========================
# BROADCAST
# =========================

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_admin(update.effective_user.id):
        return

    pesan = " ".join(context.args)

    c.execute("SELECT user_id FROM users")

    users = c.fetchall()

    sukses = 0

    for user in users:

        try:

            await context.bot.send_message(
                user[0],
                pesan
            )

            sukses += 1

        except:
            pass

    await update.message.reply_text(
        f"Broadcast terkirim ke {sukses} user"
    )

# =========================
# RUN BOT
# =========================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("stats", stats))
app.add_handler(CommandHandler("broadcast", broadcast))
app.add_handler(CommandHandler("addpremium", addpremium))

app.add_handler(CallbackQueryHandler(button))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        cek_nomor
    )
)

print("Bot berjalan...")

app.run_polling()
