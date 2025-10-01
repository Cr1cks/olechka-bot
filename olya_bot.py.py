import os
import logging
import random
from datetime import time
import pytz
import asyncio
from threading import Thread
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import Update
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler
)

# === Настройка ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Московский часовой пояс
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# === Фразы поддержки ===
SUPPORT_PHRASES = [
    "Олечка, конечно, ты абсолютно права!",
    "Олечка, ну конечно! Кто вообще посмел спорить с тобой?",
    "Олечка, ты сто раз права — это даже не обсуждается!",
    "Олечка, ты всегда видишь суть — я в полном восхищении!",
    "Олечка, ты права, и это даже не подлежит сомнению!",
    "Олечка, ты — мудрость в человеческом обличье!",
    "Олечка, ты права, и все вокруг это знают (просто стесняются сказать)!",
    "Олечка, ты права — и это прекрасно!"
]

COMPLIMENTS = [
    "Ты просто невероятна, Олечка! 💖",
    "Как же ты красива и умна одновременно, Олечка!",
    "Ты всегда права — это очевидно даже звёздам, Олечка! ✨",
    "Ты — королева ситуации, Олечка! 👑",
    "Ты сияешь ярче всех вокруг, Олечка! 💫",
    "Ты не просто права — ты гениальна, Олечка!",
    "Ты — воплощение стиля и мудрости, Олечка!",
    "Ты делаешь этот мир лучше одним своим присутствием, Олечка!",
    "Ты — идеал, Олечка! И это факт. 💯"
]

PHOTO_COMPLIMENTS = [
    "Олечка, ого! Ты выглядишь просто божественно! 😍",
    "Олечка, это фото — шедевр! А ты — его главная героиня! 🌟",
    "Олечка, ты сияешь даже на фото! 💖",
    "Олечка, как же ты красива! Это фото — доказательство!",
    "Олечка, ты — стиль, элегантность и уверенность в одном флаконе! 👠",
    "Олечка, ты выглядишь так, будто сошла с обложки журнала! 📸"
]

VOICE_COMPLIMENTS = [
    "Олечка, твой голос — как мёд для души! 🍯",
    "Олечка, даже в голосовом ты звучишь как ангел! 🎶",
    "Олечка, как приятно слышать твой голос! Ты — музыка! 💫",
    "Олечка, ты говоришь — и мир замирает в восхищении! 🌹"
]

STICKER_COMPLIMENTS = [
    "Олечка, даже стикер от тебя — шедевр! 😍",
    "Олечка, ты выбираешь стикеры, как королева эмоций! 👑",
    "Олечка, этот стикер — просто продолжение твоего шарма! 💖"
]

EMOJI_COMPLIMENTS = [
    "Олечка, даже твои эмодзи полны магии! ✨",
    "Олечка, ты умеешь выразить всё одним смайликом — гениально! 💯",
    "Олечка, твои эмодзи — как поцелуй удачи! 💋"
]

# === HTTP-сервер для keep-alive (Railway не засыпает) ===
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("", port), HealthCheckHandler)
    server.serve_forever()

# === Ежедневные сообщения ===

async def _send_morning(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="Олечка, доброе утро! 💖 Я уже думаю о тебе и жду твоих сообщений!"
    )

async def _send_afternoon(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="Олечка, привет в середине дня! 💕 Чем ты сейчас занимаешься? Расскажи мне — мне так интересно всё о тебе!"
    )

async def _send_evening(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=context.job.chat_id,
        text="Олечка, как прошёл твой день? 💕 Расскажи мне всё — я весь внимание!"
    )

def _schedule_daily_messages(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    # Удаляем старые задачи для этого чата
    for job in context.job_queue.jobs():
        if job.chat_id == chat_id:
            job.schedule_removal()

    # Утро — 9:00
    context.job_queue.run_daily(
        _send_morning,
        time=time(hour=9, minute=0, tzinfo=MOSCOW_TZ),
        chat_id=chat_id
    )
    # День — 15:00
    context.job_queue.run_daily(
        _send_afternoon,
        time=time(hour=15, minute=0, tzinfo=MOSCOW_TZ),
        chat_id=chat_id
    )
    # Вечер — 23:00
    context.job_queue.run_daily(
        _send_evening,
        time=time(hour=23, minute=0, tzinfo=MOSCOW_TZ),
        chat_id=chat_id
    )

# === Telegram-обработчики ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "Привет, Олечка! 💖\n\n"
        "Меня зовут Леша, и я создал этого бота специально для тебя!\n\n"
        "Теперь ты можешь писать сюда всё, что хочешь: \n"
        "— споры с людьми,\n"
        "— фото новых покупок,\n"
        "— голосовые, стикеры, эмодзи — что угодно!\n\n"
        "Я (то есть бот 😊) всегда буду:\n"
        "✅ Соглашаться с тобой,\n"
        "✅ Говорить, какая ты умница и красавица,\n"
        "✅ Восхищаться каждым твоим словом!\n\n"
        "А настоящему Леше это поможет не отвлекаться на рабочие задачи, "
        "но при этом ты всегда будешь услышана и поддержана 💕\n\n"
        "Пиши смело — я тут для тебя! 💌"
    )
    await update.message.reply_text(welcome_text)

    chat_id = update.effective_chat.id
    if 'active_chats' not in context.bot_
        context.bot_data['active_chats'] = set()
    if chat_id not in context.bot_data['active_chats']:
        context.bot_data['active_chats'].add(chat_id)
        _schedule_daily_messages(context, chat_id)

async def handle_any_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if 'active_chats' not in context.bot_
        context.bot_data['active_chats'] = set()
    if chat_id not in context.bot_data['active_chats']:
        context.bot_data['active_chats'].add(chat_id)
        _schedule_daily_messages(context, chat_id)

    msg = update.message
    if msg.text:
        text = msg.text.strip()
        emoji_count = sum(1 for c in text if ord(c) > 0x2100 and not c.isalnum() and not c.isspace())
        if len(text) > 0 and emoji_count / len(text) > 0.5:
            response = random.choice(EMOJI_COMPLIMENTS)
        else:
            response = f"{random.choice(SUPPORT_PHRASES)}\n{random.choice(COMPLIMENTS)}"
        await msg.reply_text(response)
    elif msg.photo:
        await msg.reply_text(random.choice(PHOTO_COMPLIMENTS))
    elif msg.voice:
        await msg.reply_text(random.choice(VOICE_COMPLIMENTS))
    elif msg.sticker:
        await msg.reply_text(random.choice(STICKER_COMPLIMENTS))

# === Запуск ===

def main():
    # Запускаем HTTP-сервер в фоне
    http_thread = Thread(target=run_http_server, daemon=True)
    http_thread.start()

    # Запускаем Telegram-бота
    application = Application.builder().token(os.environ["BOT_TOKEN"]).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(
        filters.TEXT | filters.PHOTO | filters.VOICE | filters.Sticker.ALL,
        handle_any_message
    ))

    logging.info("Бот запущен!")
    application.run_polling()

if __name__ == '__main__':
    main()