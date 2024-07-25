import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.message.chat_id, text="Привет! Я бот для оповещений Сарафан.")

async def connect(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from app.models import Partner # Импортируем модель Partner здесь
    from app import db, create_app # Импортируем db и create_app здесь

    app = create_app()
    app.app_context().push()

    chat_id = update.message.chat_id
    logging.info(f"Получено сообщение от chat_id: {chat_id}")

    try:
        code = context.args[0]
        logging.info(f"Получен код: {code}")
    except IndexError:
        logging.info("Ошибка: код не найден в сообщении")
        await context.bot.send_message(chat_id=update.message.chat_id, text='Неверный формат команды. Используйте: `/connect <код>`')
        return

    partner = Partner.query.filter_by(unique_code=code).first()
    if partner:
        logging.info(f"Найден партнер: {partner}")
        partner.telegram_chat_id = chat_id
        db.session.commit()
        await context.bot.send_message(chat_id=update.message.chat_id, text='Telegram-оповещения успешно подключены!')
    else:
        logging.info(f"Партнер с кодом {code} не найден")
        await context.bot.send_message(chat_id=update.message.chat_id, text='Неверный код. Пожалуйста, проверьте код и попробуйте снова.')

def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    application = ApplicationBuilder().token(os.environ.get("TELEGRAM_BOT_TOKEN")).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("connect", connect))

    logging.info("Бот запущен и опрашивает обновления...")
    application.run_polling()

if __name__ == '__main__':
    main()