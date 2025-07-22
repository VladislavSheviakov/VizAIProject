import os
import json
import base64
from datetime import datetime
from flask import Flask, request, jsonify
import openai

# === Настройки ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = OPENAI_API_KEY
INPUT_DIR = "input_images"
OUTPUT_DIR = "output_images"

app = Flask(__name__)


@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    user_id = data.get("user_id")
    username = data.get("username")
    caption = data.get("caption")
    input_image = data.get("input_image")  # относительный путь
    image_path = os.path.join(INPUT_DIR, os.path.basename(input_image))

    # 1. Кодируем изображение в base64
    with open(image_path, "rb") as img_file:
        base64_img = base64.b64encode(img_file.read()).decode("utf-8")

    # 2. Генерируем промт через OpenAI
    system_prompt = (
        "Ты визуальный помощник. Пользователь прислал фото и подпись. "
        "Составь краткий промт для DALL·E 3: сохрани композицию, стиль и реализм. "
        "Не добавляй новых деталей."
    )
    try:
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Комментарий: {caption}"},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_img}"}}
                    ]
                }
            ],
            max_tokens=300
        )
        final_prompt = response.choices[0].message.content.strip()
        return jsonify({"success": True, "prompt": final_prompt})
    except Exception as e:
        print("Ошибка:", str(e))
        return jsonify({"success": False, "error": str(e)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
