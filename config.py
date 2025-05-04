import os
from dotenv import load_dotenv

# بارگذاری متغیرهای محیطی از فایل .env
load_dotenv()

# اطلاعات API تلگرام
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
BOT_TOKEN = os.getenv('BOT_TOKEN')
SESSION_NAME = os.getenv('SESSION_NAME', 'tg_music_downloader')

# آدرس ربات مقصد
TARGET_BOT = "@دلخواه"

# تعداد فایل موسیقی در هر دسته
BATCH_SIZE = 100

# حداکثر تعداد پیام‌هایی که پردازش می‌شود (برای جلوگیری از پردازش بیش از حد کانال‌های بزرگ)
MAX_MESSAGES = 50000 