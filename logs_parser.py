import os
import json

LOGS_DIR = "logs"
PROMPTS_LOG = os.path.join(LOGS_DIR, "prompts_log.jsonl")


def read_logs():
    """Выводит весь лог в красивом формате."""
    if not os.path.exists(PROMPTS_LOG):
        print(f"Файл {PROMPTS_LOG} не найден.")
        return
    with open(PROMPTS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                print(json.dumps(obj, ensure_ascii=False, indent=4))
            except Exception as e:
                print(f"Ошибка чтения строки: {e}")


def filter_logs_by_user(user_id):
    """Фильтрует все записи по user_id и выводит их красиво."""
    if not os.path.exists(PROMPTS_LOG):
        print(f"Файл {PROMPTS_LOG} не найден.")
        return
    with open(PROMPTS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if str(obj.get("user_id")) == str(user_id):
                    print(json.dumps(obj, ensure_ascii=False, indent=4))
            except Exception as e:
                print(f"Ошибка чтения строки: {e}")


def filter_logs_by_log_id(log_id):
    """Фильтрует все записи по log_id и выводит их красиво."""
    if not os.path.exists(PROMPTS_LOG):
        print(f"Файл {PROMPTS_LOG} не найден.")
        return
    with open(PROMPTS_LOG, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                if obj.get("log_id") == log_id:
                    print(json.dumps(obj, ensure_ascii=False, indent=4))
            except Exception as e:
                print(f"Ошибка чтения строки: {e}")


if __name__ == "__main__":
    print("Пример использования:")
    print("read_logs() — вывести все логи")
    print("filter_logs_by_user(user_id) — фильтр по user_id")
    print("filter_logs_by_log_id(log_id) — фильтр по log_id")
