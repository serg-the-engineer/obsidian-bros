import os
import time
import shutil
import datetime
import subprocess
import glob
import json
import socket
from faster_whisper import WhisperModel
from openai import OpenAI

# --- ПУТИ ---
HOME = os.path.expanduser("~")
VOICE_MEMOS_DIR = os.path.join(
    HOME, "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
LONG_TERM_STORAGE = os.path.join(HOME, "Sergs/Надиктовано")

# Obsidian
OBSIDIAN_VAULT_ROOT = os.path.join(HOME, "Obsidian/HappySergsVault")
JOURNAL_DIR = os.path.join(OBSIDIAN_VAULT_ROOT, "Дневник")
NOTES_DIR = os.path.join(OBSIDIAN_VAULT_ROOT, "Аудиозаметки")

# Имя папки-ссылки внутри Obsidian
OBSIDIAN_AUDIO_LINK_NAME = "AudioLinks"

HISTORY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".processed_history"
)

# --- НАСТРОЙКИ AI ---
WHISPER_SIZE = "turbo" # "large-v3"
OLLAMA_MODEL = "qwen3:8b"


def log(msg):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")


def send_notification(title, message):
    script = f'display notification "{message}" with title "{title}" sound name "Glass"'
    subprocess.run(["osascript", "-e", script])


def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def manage_ollama(action, was_running_initially=False):
    if action == "start":
        if is_port_open(11434):
            return False
        else:
            log(f"Запуск Ollama ({OLLAMA_MODEL})...")
            subprocess.Popen(
                ["ollama", "serve"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            attempts = 0
            while not is_port_open(11434) and attempts < 15:
                time.sleep(2)
                attempts += 1
            return True
    elif action == "stop":
        if was_running_initially:
            subprocess.run(["pkill", "ollama"], check=False)


def transcribe(file_path):
    log(f"Whisper слушает: {os.path.basename(file_path)}")
    # vad_filter=True убирает "глюки" в тишине
    model = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(
        file_path, beam_size=5, language="ru", vad_filter=True
    )

    # Собираем текст, игнорируя пустые сегменты
    text_parts = [s.text.strip() for s in segments if s.text.strip()]
    return " ".join(text_parts)


def analyze_and_format(text, file_creation_dt):
    log("AI анализирует (структура + форматирование)...")
    client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    date_today = file_creation_dt.strftime("%Y-%m-%d")
    date_yesterday = (file_creation_dt - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    date_today_str = file_creation_dt.strftime("%Y-%m-%d")
    date_yesterday_str = (file_creation_dt - datetime.timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )

    prompt = f"""
    Текст аудиозаписи (сырой): "{text}"

    Дата записи: {date_today} (Время {file_creation_dt.strftime("%H:%M")}, {file_creation_dt.strftime("%A")}).
    Вчерашняя дата: {date_yesterday}.

    Твои задачи:
    1. **Тип**: "Заметка" или "Дневник". Используй "Заметка", если в тексте нет упоминаний о сне, здоровье, успехах или оценке дня.
        Если в начале упоминается какая-то конкретная дата, скорее всего будет дневник.
    2. **Логическая дата (logical_date)**. Критически важно определить, о какой дате говорит автор. Используй приоритеты:
       - **ПРИОРИТЕТ 1 (Явное указание)**: Если автор говорит "Сегодня 23 ноября" или "Запись за воскресенье", а файл создан 24-го - ВЕРНИ 20251123. Верь голосу, а не файлу.
       - **ПРИОРИТЕТ 2 (Ночной режим)**: Если явной даты нет, но время записи 00:00-06:00 и автор подводит итоги дня — верни дату ВЧЕРА ({date_yesterday_str}).
       - **ПРИОРИТЕТ 3 (По умолчанию)**: Если ничего из вышеперечисленного — верни техническую дату ({date_today_str}).
       Формат вывода даты строго: YYYYMMDD.

    3. **Структура (только для Дневника)**:
       - "sleep": Сон.
       - "health": Здоровье/боли.
       - "successes": Успехи.
       - "score": Оценка дня.
        Выдели точные факты, и желательно без форматирования и обобщений сон и здоровье. Для успехов делай краткую сводку. Для оценки дня делай число от 1 до 5, где 5 - отличный день. После точки краткое пояснение.
    4. **Formatted Transcript**: Возьми "Текст аудиозаписи" и расставь абзацы, чтобы его было удобно читать. Не сокращай текст, сохрани все слова, просто сделай читабельно.

    Верни JSON:
    {{
        "type": "Дневник" или "Заметка",
        "logical_date": "YYYYMMDD",
        "sleep": "...",
        "health": "...",
        "successes": "...",
        "score": "...",
        "formatted_transcript": "Текст с абзацами..."
    }}
    """

    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        log(f"Ошибка LLM: {e}")
        # Fallback: возвращаем сырой текст, если AI упал
        return {
            "type": "Дневник",
            "logical_date": date_today.replace("-", ""),
            "formatted_transcript": text,
            "sleep": "",
            "health": "",
            "successes": "",
            "score": "",
        }


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r") as f:
        return set(line.strip() for line in f)


def save_to_history(filename):
    with open(HISTORY_FILE, "a") as f:
        f.write(filename + "\n")


def main():
    if not os.path.exists(VOICE_MEMOS_DIR):
        log("Папка Диктофона не найдена.")
        return

    all_files = glob.glob(os.path.join(VOICE_MEMOS_DIR, "*.m4a"))
    processed_files = load_history()
    new_files = [f for f in all_files if os.path.basename(f) not in processed_files]

    if not new_files:
        return

    log(f"Новых файлов: {len(new_files)}")
    we_started_ollama = manage_ollama("start")
    success_count = 0

    try:
        for folder in [LONG_TERM_STORAGE, JOURNAL_DIR, NOTES_DIR]:
            os.makedirs(folder, exist_ok=True)

        for file_path in new_files:
            original_filename = os.path.basename(file_path)
            if os.path.getsize(file_path) < 1000:
                continue

            try:
                # 1. Подготовка
                creation_dt = datetime.datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                )
                time_part = creation_dt.strftime("%H%M")
                temp_path = f"/tmp/{original_filename}"
                shutil.copy2(file_path, temp_path)

                # 2. Обработка (Whisper + AI)
                raw_text = transcribe(temp_path)
                analysis = analyze_and_format(raw_text, creation_dt)

                note_type = analysis.get("type", "Дневник").capitalize()
                logical_date = analysis.get(
                    "logical_date", creation_dt.strftime("%Y-%m-%d")
                )

                # Данные для дневника
                sleep_txt = analysis.get("sleep", "")
                health_txt = analysis.get("health", "")
                success_txt = analysis.get("successes", "")
                score_txt = analysis.get("score", "")

                # Здесь мы берем уже отформатированный текст с абзацами
                final_text_content = analysis.get("formatted_transcript", raw_text)

                # 3. Аудио (перемещение)
                final_audio_name = f"{note_type}_{logical_date}_{time_part}.m4a"
                final_audio_path = os.path.join(LONG_TERM_STORAGE, final_audio_name)

                counter = 1
                while os.path.exists(final_audio_path):
                    final_audio_name = (
                        f"{note_type}_{logical_date}_{time_part}_{counter}.m4a"
                    )
                    final_audio_path = os.path.join(LONG_TERM_STORAGE, final_audio_name)
                    counter += 1

                shutil.move(temp_path, final_audio_path)

                # Ссылка для Obsidian
                obsidian_audio_link = (
                    f"![[{OBSIDIAN_AUDIO_LINK_NAME}/{final_audio_name}]]"
                )

                # 4. Сборка Markdown
                if note_type == "Заметка":
                    target_dir = NOTES_DIR
                    md_name = f"{logical_date}_{time_part}.md"

                    md_content = f"""---
date: {logical_date}
time: {time_part}
type: заметка
---
# Заметка {time_part}

{final_text_content}

---
## Исходный текст
{obsidian_audio_link}
"""
                else:
                    # ДНЕВНИК
                    target_dir = JOURNAL_DIR
                    # Имя файла как вы хотели: дата_время
                    md_name = f"{logical_date}.md"

                    structure_block = ""
                    if sleep_txt:
                        structure_block += f"**Сон**: {sleep_txt}\n\n"
                    if health_txt:
                        structure_block += f"**Боли**: {health_txt}\n\n"
                    if success_txt:
                        structure_block += f"**Успехи**: {success_txt}\n\n"
                    if score_txt:
                        structure_block += f"**Оценка дня**: {score_txt}\n\n"

                    md_content = f"""---
date: {logical_date}
type: дневник
---
[[Дневник]]

{structure_block}

---
---
## Полный транскрипт

{obsidian_audio_link}

{final_text_content}
"""

                md_path = os.path.join(target_dir, md_name)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(md_content)

                save_to_history(original_filename)
                success_count += 1
                log(f"[{note_type}] Готово: {md_name}")

            except Exception as e:
                log(f"FAIL {original_filename}: {e}")

        # Git Sync
        if success_count > 0:
            subprocess.run(
                ["git", "add", "."],
                cwd=OBSIDIAN_VAULT_ROOT,
                stdout=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                ["git", "commit", "-m", f"Journal AI: {success_count} entries"],
                cwd=OBSIDIAN_VAULT_ROOT,
                stdout=subprocess.DEVNULL,
                check=False,
            )
            subprocess.run(
                ["git", "push", "origin", "master"],
                cwd=OBSIDIAN_VAULT_ROOT,
                stdout=subprocess.DEVNULL,
                check=False,
            )

    finally:
        manage_ollama("stop", was_running_initially=we_started_ollama)
        if success_count > 0:
            send_notification("Journal AI", f"Обработано: {success_count}")


if __name__ == "__main__":
    main()
