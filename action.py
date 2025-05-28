import os, requests
from datetime import time, datetime, timedelta
from babel.dates import format_date
from pytz import timezone
from flask import Flask, request
from telegram import Update,Bot
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
)

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
TOKEN=os.getenv('TOKEN')
CHAT_ID=os.getenv('CHATID')
OWNER_ID=int(os.getenv('OWNER'))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
# 🌍 Часовий пояс
KYIV_TZ = timezone('Europe/Kyiv')


alertText='Ця команда доступна лише власнику бота. @yourbus_travel'
# Глобальна змінна для зберігання ID групи
chat_ids = set()


app = Flask(__name__)
bot = Bot(token=TOKEN)

application = ApplicationBuilder().token(TOKEN).build()



def get_date_range_text():
    tomorrow = datetime.now() + timedelta(days=1)
    day_after_tomorrow = datetime.now() + timedelta(days=2)

    if tomorrow.month == day_after_tomorrow.month:
        month_name_uk=format_date(tomorrow, format='d MMMM yyyy',locale='uk').split()[1]
        date_range = f"{tomorrow.day}-{day_after_tomorrow.day} {month_name_uk}"
    else:
        month1_name_uk = format_date(tomorrow, format='d MMMM yyyy',locale='uk').split()[1]
        month2_name_uk = format_date(day_after_tomorrow, format='d MMMM yyyy',locale='uk').split()[1]
        date_range = f"{tomorrow.day} {month1_name_uk} – {day_after_tomorrow.day} {month2_name_uk}"

    return date_range

def message():
    period = get_date_range_text()
    return f"Доброго дня ☘️\n\n📣✅Прохання звʼязатися з усіма вашими пасажирами , котрі заброньовані на {period} уточнити чи їдуть та підтвердити в системі.\n\nДякуємо🤝😊"


# 🕘 Повідомлення
async def daily_message(context: ContextTypes.DEFAULT_TYPE):
   await context.bot.send_message(chat_id=CHAT_ID, text=message())


# 📅 Старт: автоматичне планування
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    job_name = f"daily_{chat_id}"

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(alertText)
        return
    default_time = time(hour=11, minute=45, tzinfo=KYIV_TZ)

    # Видалення попереднього джоба (якщо є)
    context.job_queue.scheduler.remove_all_jobs()
    context.job_queue.run_daily(
        callback=daily_message,
        time=default_time,
        chat_id=chat_id,
        name=job_name
    )


    await update.message.reply_text(f"✅ Щоденні повідомлення будуть надсилатись щодня о {default_time.hour:02d}:{default_time.minute:02d} (за Києвом).")


# ⏱ Користувач задає час у форматі hh:mm
async def settime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    job_name = f"daily_{chat_id}"

    try:
        if update.effective_user.id != OWNER_ID:
            await update.message.reply_text(alertText)
            return
        time_arg = context.args[0]
        hour, minute = map(int, time_arg.split(":"))

        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError

        context.job_queue.scheduler.remove_all_jobs()
        context.job_queue.run_daily(
            callback=daily_message,
            time=time(hour=hour, minute=minute, tzinfo=KYIV_TZ),
            chat_id=chat_id,
            name=job_name
        )


        await update.message.reply_text(
            f"✅ Повідомлення буде надсилатись щодня о {hour:02d}:{minute:02d} (за Києвом)."
        )

    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Формат: /settime HH:MM (наприклад, /settime 7:30)")


# ⛔ Зупинка щоденних повідомлень
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    job_name = f"daily_{chat_id}"
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(alertText)
        return
    jobs = context.job_queue.get_jobs_by_name(job_name)
    if jobs:
        for job in jobs:
            job.schedule_removal()

        await update.message.reply_text("🛑 Щоденні повідомлення вимкнено.")
    else:
        await update.message.reply_text("ℹ️ Немає активного щоденного розкладу.")

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text(alertText)
        print(update.effective_user.id)
        return
    try:
        await daily_message(context)
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Повідомлення не надіслано")


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    for msg_id in range(update.message.message_id, update.message.message_id - 50, -1):
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except:
            pass  # Можливо, повідомлення не існує або бот не має доступу

async def handle_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    chat_title = update.effective_chat.title or update.effective_chat.username

    if chat_id not in chat_ids:
        print(f"📌 Знайдено новий чат: {chat_id} — {chat_title}")
        chat_ids.add(chat_id)

    await context.bot.forward_message(
        chat_id=OWNER_ID,
        from_chat_id=chat_id,
        message_id=update.message.message_id
    )
    #delete not relevant message
    if chat_id != int(CHAT_ID):
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=update.message.message_id)
        except Exception as e:
            print(f"Помилка при видаленні: {e}")


# 🚀 Запуск
# if __name__ == '__main__':
#     bot = Application.builder().token(TOKEN).build()
#
#     bot.add_handler(CommandHandler("start", start))
#     bot.add_handler(CommandHandler("send", send))
#     bot.add_handler(CommandHandler("settime", settime))
#     bot.add_handler(CommandHandler("stop", stop))
#     bot.add_handler(CommandHandler("clear", clear_chat))
#
#     # Бот реагує на будь-яке повідомлення
#     bot.add_handler(MessageHandler(filters.ALL, handle_chat_id))
#     print("🤖 Бот працює.")
#     bot.run_polling()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("send", send))
application.add_handler(CommandHandler("settime", settime))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("clear", clear_chat))

@app.route(f"/{WEBHOOK_SECRET}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    application.update_queue.put_nowait(update)

    return "ok"

# Health check
@app.route("/", methods=["GET"])
def home():
    return "Бот працює."


if __name__ == "__main__":
    # Встановлення webhook
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    full_url = f"{os.getenv('WEBHOOK_URL')}/{WEBHOOK_SECRET}"
    r = requests.get(url, params={"url": full_url})
    print("🔗 Webhook статус:", r.text)

    # Запуск Telegram застосунку з webhook
    print("PORT:", os.getenv("PORT"))
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 5000)),
        webhook_url=full_url,
        secret_token=WEBHOOK_SECRET
    )
