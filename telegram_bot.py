import logging
import base64
import os
import json
from datetime import datetime
from enum import Enum, auto
import re
import random
import shutil

import openai
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler,
    MessageHandler, ContextTypes, ConversationHandler, filters
)

# === 🔑 Загружаем .env ===
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
openai.api_key = OPENAI_API_KEY

# === Состояния FSM через Enum ===


class States(Enum):
    WAIT_RENDER_IMAGE = auto()
    WAIT_FEEDBACK = auto()
    WAIT_PAYMENT = auto()
    WAIT_EMAIL = auto()

# === Основной бот ===


class ChatGPTTelegramBot:
    def log_generation(self, user_id: int):
        """
        Записывает одну строку лога успешной генерации в logs/prompts_log.jsonl
        """
        log_path = os.path.join(self.logs_dir, "prompts_log.jsonl")
        record = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    """
    Telegram-бот для генерации промтов с помощью GPT-4o и обработки пользовательских команд.
    """

    def __init__(self, token: str):
        """
        Инициализация бота, настройка логирования и регистрация хендлеров.
        :param token: Токен Telegram-бота
        """
        self.token = token

        # Инициализация Telegram приложения
        self.app: Application = ApplicationBuilder().token(self.token).build()

        # Логирование
        if not os.path.exists("app.log"):
            open("app.log", "w").close()
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("app.log", encoding="utf-8"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

        self.input_dir = "input_images"
        self.output_dir = "output_images"
        self.logs_dir = "logs"
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)

        # === FSM: ConversationHandler для /render ===
        conv_handler_render = ConversationHandler(
            entry_points=[CommandHandler("render", self.render)],
            states={
                States.WAIT_RENDER_IMAGE: [
                    MessageHandler(
                        filters.PHOTO & filters.Caption(), self.handle_image)
                ],
                States.WAIT_FEEDBACK: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, self.handle_feedback)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        # === FSM: ConversationHandler для /buy ===
        conv_handler_buy = ConversationHandler(
            entry_points=[CommandHandler("buy", self.buy)],
            states={
                States.WAIT_PAYMENT: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, self.handle_payment)
                ],
                States.WAIT_EMAIL: [
                    MessageHandler(filters.TEXT & ~
                                   filters.COMMAND, self.handle_email)
                ],
            },
            fallbacks=[CommandHandler("cancel", self.cancel)],
        )

        # === Регистрируем хендлеры ===
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("stats", self.stats))
        self.app.add_handler(conv_handler_render)
        self.app.add_handler(conv_handler_buy)

    # === /start ===
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("👋 Привет! Я рендер-бот.\nИспользуй /render, /buy, /stats или /help")

    # === /help ===
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "ℹ️ Доступные команды:\n"
            "/start — приветствие\n"
            "/render — отправить фото для рендера\n"
            "/buy — оформить оплату\n"
            "/stats — статистика генераций\n"
            "/cancel — отменить процесс"
        )

    # === /stats ===
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        count = 0
        if os.path.exists("prompts_log.jsonl"):
            with open("prompts_log.jsonl", "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
        await update.message.reply_text(f"📊 Сгенерировано промтов: {count}")
        log_path = os.path.join(self.logs_dir, "prompts_log.jsonl")
        count = 0
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                count = sum(1 for _ in f)
        await update.message.reply_text(f"Всего успешных генераций: {count}")

    # === /cancel ===
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ Операция отменена.")
        return ConversationHandler.END

    # === /buy ===
    async def buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("💳 Напиши 'Оплатил', когда завершишь оплату.")
        return States.WAIT_PAYMENT

    async def handle_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📧 Теперь пришли свой email.")
        return States.WAIT_EMAIL

    async def handle_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        email = update.message.text
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            await update.message.reply_text("⚠️ Похоже, это не email. Попробуйте ещё раз.")
            return States.WAIT_EMAIL
        self.logger.info(f"Email от пользователя: {email}")
        await update.message.reply_text(f"✅ Email '{email}' получен. Спасибо!")
        return ConversationHandler.END

    # === /render ===
    async def render(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("📸 Пришли изображение с подписью.")
        return States.WAIT_RENDER_IMAGE

    async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        message = update.message
        if not message.photo:
            await message.reply_text("⚠️ Фото не найдено, пришли ещё раз.")
            return

        # Генерируем уникальный 8-значный номер
        img_num = f"{random.randint(10000000, 99999999)}"
        user_id = update.effective_user.id
        caption = message.caption or "Без описания"
        # Чистим caption только для лога
        clean_caption = re.sub(r'[\\/:*?"<>|]', '', caption)

        # 1) Определяем порядковый номер (ищем последние order_num для img_num)
        prompts_log_path = os.path.join(self.logs_dir, "prompts_log.jsonl")
        order_num = 1
        if os.path.exists(prompts_log_path):
            with open(prompts_log_path, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry.get("input_image", "").startswith(img_num):
                            num = entry["input_image"].split(
                                "_")[-1].split(".")[0]
                            if num.isdigit():
                                order_num = max(order_num, int(num) + 1)
                    except Exception:
                        continue
        order_num_str = f"{order_num:02d}"

        # 2) Сохраняем оригинал фото в input_images
        input_filename = f"{img_num}_{order_num_str}.jpg"
        input_path = os.path.join(self.input_dir, input_filename)

        await message.reply_text("📥 Скачиваю изображение...")
        try:
            
            file = await context.bot.get_file(message.photo[-1].file_id)
            await file.download_to_drive(input_path)

            # 3) Сохраняем выходной файл в output_images с совпадающим img_num и order_num
            output_filename = f"{img_num}_{order_num_str}.jpg"
            output_path = os.path.join(self.output_dir, output_filename)
            shutil.copy(input_path, output_path)

            # 4) Кодируем в base64 из output_images
            with open(output_path, "rb") as img_file:
                base64_img = base64.b64encode(img_file.read()).decode("utf-8")

            await message.reply_text("🤖 GPT-4o генерирует промт...")

            # GPT системный промт
            system_prompt = (
                "Ты визуальный помощник. Пользователь прислал фото и подпись. "
                "Составь краткий промт для DALL·E 3: сохрани композицию, стиль и реализм. "
                "Не добавляй новых деталей."
            )

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": [
                        {"type": "text", "text": f"Комментарий: {caption}"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_img}"}}
                    ]}
                ],
                max_tokens=300
            )

            final_prompt = response.choices[0].message.content.strip()

            # 5) Сохраняем файл промта в output_images
            prompt_filename = f"{img_num}_{order_num_str}_prompt.txt"
            prompt_path = os.path.join(self.output_dir, prompt_filename)
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(final_prompt)

            # 6) Логируем в prompts_log.jsonl по новой структуре
            log_id = f"{img_num}_{order_num_str}"
            prompt_data = {
                "log_id": log_id,
                "timestamp": datetime.now().isoformat(),
                "username": update.effective_user.username,
                "user_id": user_id,
                "input_image": os.path.join(self.input_dir, input_filename).replace("\\", "/"),
                "prompt": final_prompt,
                "caption": clean_caption,
                "output_image": os.path.join(self.output_dir, output_filename).replace("\\", "/")
            }
            with open(prompts_log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(prompt_data, ensure_ascii=False) + "\n")

            self.logger.info(f"GPT-4o промт: {final_prompt}")
            await message.reply_text(f"✅ GPT-4o промт:\n{final_prompt}")

            # Запрашиваем фидбек
            await message.reply_text("✏️ Если хочешь, напиши отзыв о работе.")
            return States.WAIT_FEEDBACK

        except Exception as e:
            await message.reply_text("❌ Произошла ошибка при обработке изображения. Попробуйте позже.")
            self.logger.error(f"Ошибка handle_image: {e}")
            return ConversationHandler.END

    def read_logs(self, log_type="prompts"):
        """
        Читает и красиво выводит JSON-логи из logs/prompts_log.jsonl или logs/feedbacks_log.jsonl
        log_type: "prompts" или "feedbacks"
        """
        log_file = os.path.join(self.logs_dir, f"{log_type}_log.jsonl")
        if not os.path.exists(log_file):
            print(f"Файл {log_file} не найден.")
            return
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    print(json.dumps(obj, ensure_ascii=False, indent=2))
                except Exception as e:
                    print(f"Ошибка чтения строки: {e}")

    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        feedback = update.message.text
        self.logger.info(f"Отзыв пользователя: {feedback}")
        await update.message.reply_text("🙏 Спасибо за отзыв!")

        feedback_data = {
            "timestamp": datetime.now().isoformat(),
            "username": update.effective_user.username,
            "user_id": update.effective_user.id,
            "feedback": feedback
        }
        feedbacks_log_path = os.path.join(self.logs_dir, "feedbacks_log.jsonl")
        with open(feedbacks_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback_data, ensure_ascii=False) + "\n")

        return ConversationHandler.END

    def run(self):
        self.logger.info("🚀 Бот запущен")
        self.app.run_polling()


# === Точка входа ===
if __name__ == '__main__':
    bot = ChatGPTTelegramBot(TELEGRAM_BOT_TOKEN)
    bot.run()
