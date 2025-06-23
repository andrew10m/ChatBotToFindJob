import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable not set!")

DATABASE_URL = os.getenv("DATABASE_URL", "job_bot.db")

# ADMIN_IDS - список ID администраторов через запятую
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(admin_id.strip()) for admin_id in ADMIN_IDS_STR.split(',') if admin_id.strip()]

# Ограничения анти-спама
MAX_VACANCIES_PER_DAY = 5
SPAM_KEYWORDS = ["быстрый заработок", "без вложений", "пирамида"] # Пример

# Настройки для FSM (если используется Redis)
# REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
# REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Пути к юридическим документам
USER_AGREEMENT_PATH = "documents/user_agreement.md"
VACANCY_AGREEMENT_PATH = "documents/vacancy_agreement.md"
PRIVACY_POLICY_PATH = "documents/privacy_policy.md"
MODERATION_POLICY_PATH = "documents/moderation_policy.md"
DATA_CONSENT_FORM_PATH = "documents/data_consent_form.md" # Может быть объединено с user_agreement
DISCLAIMER_NOTICE_PATH = "documents/disclaimer_notice.txt"
