from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, ContextTypes)
from telegram.ext import filters
import sqlite3
import datetime
import csv
import os

#TELEGRAM/
TELETOKEN=os.environ['TELEGRAMBOT_TOKEN']

#Database
DBFILE="/opt/bloodpressure.db"

# Konversationsstufen
SYS, DIA, PULSE, CONFIRM_DELETE = range(4)

# Verbindung zur SQLite-Datenbank
def init_db():
    conn = sqlite3.connect(DBFILE)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS measurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        sys INTEGER,
        dia INTEGER,
        pulse INTEGER,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

# Messung starten
async def start_new_measurement(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Bitte geben Sie den systolischen Wert (SYS) ein:",
    )
    return SYS

# SYS Wert speichern
async def save_sys(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.message.text)
        if value < 30 or value > 250:  # Gültigkeitsbereich anpassen
            raise ValueError
        context.user_data["sys"] = value
        await update.message.reply_text(
            "Bitte geben Sie den diastolischen Wert (DIA) ein:"
        )
        return DIA
    except ValueError:
        await update.message.reply_text(
            "Ungültiger Wert! Bitte geben Sie einen numerischen Wert zwischen 30 und 250 ein. Abbruch mit /cancel"
        )
        return SYS

# DIA Wert speichern
async def save_dia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.message.text)
        if value < 30 or value > 180:  # Gültigkeitsbereich anpassen
            raise ValueError
        context.user_data["dia"] = value
        await update.message.reply_text(
            "Bitte geben Sie den Pulswert ein:"
        )
        return PULSE
    except ValueError:
        await update.message.reply_text(
            "Ungültiger Wert! Bitte geben Sie einen numerischen Wert zwischen 30 und 180 ein. Abbruch mit /cancel"
        )
        return DIA

# Puls speichern und in DB ablegen
async def save_pulse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.message.text)
        if value < 30 or value > 250:  # Gültigkeitsbereich anpassen
            raise ValueError
        context.user_data["pulse"] = value
        user_id = update.message.from_user.id
        sys = context.user_data["sys"]
        dia = context.user_data["dia"]
        pulse = context.user_data["pulse"]

        # Datenbankeintrag
        conn = sqlite3.connect(DBFILE)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO measurements (user_id, sys, dia, pulse) VALUES (?, ?, ?, ?)",
                       (user_id, sys, dia, pulse))
        conn.commit()
        conn.close()

        await update.message.reply_text(
            f"Danke! Ihre Werte wurden gespeichert:\nSYS: {sys}, DIA: {dia}, Puls: {pulse}",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "Ungültiger Wert! Bitte geben Sie einen numerischen Wert zwischen 30 und 250 ein. Abbruch mit /cancel"
        )
        return PULSE

# Abbrechen der Messung
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Messung abgebrochen.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# Messungen anzeigen
async def show_measurements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    conn = sqlite3.connect(DBFILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sys, dia, pulse, timestamp FROM measurements WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # Tabellenkopf
        message = "```\n"  # Monospace-Formatierung starten
        message += f"{'Datum/Zeit':<20}{'SYS':<6}{'DIA':<6}{'PULS':<6}\n"
        message += "-" * 35 + "\n"
        # Datenzeilen hinzufügen
        for sys, dia, pulse, timestamp in rows:
            # Zeitformatierung
            formatted_time = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
            message += f"{formatted_time:<20}{sys:<6}{dia:<6}{pulse:<6}\n"            

        message += "```"  # Monospace-Formatierung beenden
    else:
        message = "Keine Messwerte gefunden."

    await update.message.reply_text(message, parse_mode="Markdown")


async def export_measurements(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    file_name = f"measurements_{user_id}.csv"

    conn = sqlite3.connect(DBFILE)
    cursor = conn.cursor()
    cursor.execute("SELECT sys, dia, pulse, timestamp FROM measurements WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()

    if rows:
        # CSV-Datei erstellen
        with open(file_name, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            # Kopfzeile schreiben
            writer.writerow(["SYS", "DIA", "PULS", "DATE"])
            # Daten schreiben
            for sys, dia, pulse, timestamp in rows:
                # Zeitformatierung
                writer.writerow([sys, dia, pulse, timestamp])

        # Datei an den Chat senden
        with open(file_name, "rb") as file:
            await update.message.reply_document(file, filename=file_name)

        # Temporäre Datei löschen
        os.remove(file_name)
    else:
        await update.message.reply_text("Keine Messwerte gefunden.")


def main():

    # Datenbank initialisieren
    init_db()
    
    # Bot initialisieren
    app = ApplicationBuilder().token(TELETOKEN).build()

    # Konversations-Handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newmeasurement", start_new_measurement)],
        states={
            SYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_sys)],
            DIA: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_dia)],
            PULSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_pulse)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Handler registrieren
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("showmeasurements", show_measurements))
    app.add_handler(CommandHandler("export", export_measurements))


    # Bot starten
    app.run_polling()

if __name__ == "__main__":
    main()

