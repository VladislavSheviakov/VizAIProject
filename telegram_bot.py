# import logging
# import base64
# import os
# import json
# from datetime import datetime
# import openai
# from dotenv import load_dotenv

# from telegram import Update
# from telegram.ext import (
#     Application, ApplicationBuilder, CommandHandler,
#     MessageHandler, ContextTypes, ConversationHandler, filters
# )

# # === 🔑 Загружаем переменные окружения из .env ===
# load_dotenv()
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# openai.api_key = OPENAI_API_KEY

# # Константа для стадии ожидания изображения после команды /render
# RENDER_WAIT_IMAGE = 1


# # === 🤖 Основной класс Telegram-бота ===
# class ChatGPTTelegramBot:
#     def __init__(self, token: str):
#         self.token = token

#         # Инициализация Telegram приложения
#         self.app: Application = ApplicationBuilder().token(self.token).build()

#         # Если лог уже есть — очищаем
#         if os.path.exists("app.log"):
#             open("app.log", "w").close()

#         # Логирование в файл и консоль
#         logging.basicConfig(
#             level=logging.INFO,
#             format="%(asctime)s - %(levelname)s - %(message)s",
#             handlers=[
#                 logging.FileHandler("app.log"),
#                 logging.StreamHandler()
#             ]
#         )
#         self.logger = logging.getLogger(__name__)

#         # === Регистрируем команды ===
#         conv_handler = ConversationHandler(
#             entry_points=[CommandHandler("render", self.render)],
#             states={
#                 RENDER_WAIT_IMAGE: [
#                     MessageHandler(filters.PHOTO & filters.Caption(), self.handle_image)
#                 ]
#             },
#             fallbacks=[CommandHandler("cancel", self.cancel)],
#         )

#         self.app.add_handler(CommandHandler("start", self.start))
#         self.app.add_handler(CommandHandler("buy", self.buy))
#         self.app.add_handler(conv_handler)

#     # === /start ===
#     async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         await update.message.reply_text("👋 Привет! Пришли изображение с подписью после команды /render")

#     # === /cancel ===
#     async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         await update.message.reply_text("❌ Отменено. Можно заново ввести /render.")
#         return ConversationHandler.END

#     # === /buy ===
#     async def buy(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         await update.message.reply_text("🛒 Покупка пока недоступна. В скором времени добавим оплату и подписку!")

#     # === /render ===
#     async def render(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         await update.message.reply_text("📸 Пришли изображение с подписью, которое хочешь улучшить.")
#         return RENDER_WAIT_IMAGE

#     # === Обработка загруженного изображения ===
#     async def handle_image(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
#         message = update.message

#         # Если нет фото — просим повторить
#         if not message.photo:
#             await message.reply_text("⚠️ Пришли изображение с подписью после /render")
#             return

#         # Извлекаем подпись и фото
#         caption = message.caption or "Без описания"
#         photo = message.photo[-1]  # самое большое фото
#         photo_path = "input.jpg"

#         await message.reply_text("📥 Загружаю изображение...")

#         try:
#             # === Скачиваем фото ===
#             file = await context.bot.get_file(photo.file_id)
#             await file.download_to_drive(photo_path)

#             # === Кодируем фото в base64 ===
#             with open(photo_path, "rb") as img_file:
#                 base64_img = base64.b64encode(img_file.read()).decode("utf-8")

#             await message.reply_text("👁️ GPT-4o анализирует изображение...")

#             # === Системный промт для GPT-4o ===
#             system_prompt = (
#                 "Ты визуальный помощник. Пользователь прислал изображение сцены и подпись. "
#                 "Составь короткий, чёткий и технический промт для генерации изображения через DALL·E 3, "
#                 "сохранив:\n"
#                 "- Композицию, геометрию и структуру сцены\n"
#                 "- Стиль, ракурс и масштаб\n"
#                 "- Никаких новых объектов или изменений. Просто усили реализм.\n"
#                 "Промт должен быть лаконичным, как для визуального рендер-движка."
#             )

#             # === Отправляем запрос в GPT-4o ===
#             response = openai.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": system_prompt},
#                     {"role": "user", "content": [
#                         {"type": "text", "text": f"Комментарий пользователя: {caption}"},
#                         {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}}
#                     ]}
#                 ],
#                 max_tokens=300
#             )

#             # === Результат GPT-4o ===
#             final_prompt = response.choices[0].message.content.strip()

#             # === Логируем в prompts_log.jsonl ===
#             prompt_data = {
#                 "timestamp": datetime.now().isoformat(),
#                 "username": update.effective_user.username,
#                 "user_id": update.effective_user.id,
#                 "caption": caption,
#                 "prompt": final_prompt
#             }

#             with open("prompts_log.jsonl", "a", encoding="utf-8") as f:
#                 f.write(json.dumps(prompt_data, ensure_ascii=False) + "\n")

#             self.logger.info(f"GPT-4o промт:\n{final_prompt}")
#             await message.reply_text(f"📄 GPT-4o сформировал промт:\n{final_prompt}")

#             # === ТВОЙ ЗАКОММЕНТИРОВАННЫЙ БЛОК ===
#             # await message.reply_text("🎨 Генерация через DALL·E 3 с учётом референса...")

#             # try:
#             #     dalle_response = openai.images.generate(
#             #         model="dall-e-3",
#             #         prompt=final_prompt,
#             #         size="1024x1024",
#             #         quality="standard",
#             #         n=1,
#             #         response_format="url",
#             #         # image={"image": base64_img}  # Используй корректный способ reference если есть API
#             #     )

#             #     image_url = dalle_response.data[0].url
#             #     await message.reply_photo(photo=image_url, caption="🖼️ Сгенерировано DALL·E 3")
#             #     self.logger.info(f"DALL·E 3 image URL: {image_url}")

#             # except Exception as e:
#             #     await message.reply_text(f"❌ Ошибка DALL·E 3: {e}")
#             #     self.logger.error(f"DALL·E error: {e}")

#         except Exception as e:
#             await message.reply_text(f"❌ Ошибка GPT-4o: {e}")
#             self.logger.error(f"GPT-4o error: {e}")
#             return

#     # === Запуск бота ===
#     def run(self):
#         self.logger.info("🚀 Бот запущен и слушает обновления")
#         self.app.run_polling()


# # === 🎯 Точка входа ===
# if __name__ == '__main__':
#     bot = ChatGPTTelegramBot(TELEGRAM_BOT_TOKEN)
#     bot.run()
