from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import requests

TOKEN = "8752615272:AAGS7COBor0kpMrcHX_LPZoUYImEJwuFiU4"
API_KEY = "d9e9eea76cc77356954de5ffbc40086a"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Kirim nomor telepon dengan kode negara.\nContoh: +628123456789"
    )

async def cek_nomor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nomor = update.message.text

    url = f"http://apilayer.net/api/validate?access_key={API_KEY}&number={nomor}"

    try:
        response = requests.get(url)
        data = response.json()

        valid = data.get("valid")
        country = data.get("country_name")
        location = data.get("location")
        carrier = data.get("carrier")
        line_type = data.get("line_type")

        if valid:
            hasil = f"""
HASIL CEK NOMOR

Nomor: {nomor}
Valid: Ya
Negara: {country}
Lokasi: {location}
Operator: {carrier}
Jenis: {line_type}
"""

            if line_type:
                if "voip" in line_type.lower():
                    hasil += "\nStatus: Kemungkinan nomor virtual / VOIP"
                else:
                    hasil += "\nStatus: Kemungkinan nomor biasa"

        else:
            hasil = "Nomor tidak valid"

        await update.message.reply_text(hasil)

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, cek_nomor))

print("Bot berjalan...")
app.run_polling()
