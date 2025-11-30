import os

HOME = os.path.expanduser("~")

# Obsidian
OBSIDIAN_VAULT_ROOT = os.path.join(HOME, "Obsidian/HappySergsVault")
JOURNAL_DIR = os.path.join(OBSIDIAN_VAULT_ROOT, "Дневник")
NOTES_DIR = os.path.join(OBSIDIAN_VAULT_ROOT, "Аудиозаметки")
ANALYSIS_DIR = os.path.join(OBSIDIAN_VAULT_ROOT, "Анализ")

# Папка где хранятся исходные записи и долгосрочное хранилище аудио
VOICE_MEMOS_DIR = os.path.join(
    HOME, "Library/Group Containers/group.com.apple.VoiceMemos.shared/Recordings"
)
LONG_TERM_STORAGE = os.path.join(HOME, "Sergs/Надиктовано")

# Имя папки-ссылки внутри Obsidian
OBSIDIAN_AUDIO_LINK_NAME = "AudioLinks"

# Локальный файл истории обработанных файлов (в корне проекта)
HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".processed_history")

# AI / Модели
WHISPER_SIZE = "turbo"  # можно переопределить в коде при необходимости
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_API_URL = "http://localhost:11434/v1"
