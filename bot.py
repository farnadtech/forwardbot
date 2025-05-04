import logging
import os
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters
)
from dotenv import load_dotenv

from handlers import (
    start_handler,
    help_handler,
    status_handler,
    message_handler,
    button_handler
)
from config import BOT_TOKEN, API_ID, API_HASH

# تنظیم لاگر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """راه‌اندازی ربات"""
    # بارگذاری متغیرهای محیطی
    load_dotenv()
    
    # چک کردن توکن ربات و تنظیمات API تلگرام
    if not BOT_TOKEN:
        logger.error("لطفاً توکن ربات را در فایل .env تنظیم کنید.")
        return
        
    if not API_ID or not API_HASH:
        logger.error("لطفاً API_ID و API_HASH تلگرام را در فایل .env تنظیم کنید.")
        return
    
    # تست اولیه اتصال به تلگرام
    try:
        from downloader import MusicDownloader
        test_client = MusicDownloader()
        if not test_client.connect():
            logger.error("اتصال اولیه به تلگرام ناموفق بود. لطفاً تنظیمات API را بررسی کنید.")
            return
        logger.info("تست اتصال به تلگرام با موفقیت انجام شد.")
        test_client.disconnect()
    except Exception as e:
        logger.error(f"خطا در تست اتصال به تلگرام: {e}")
        return
        
    # ایجاد آپدیتر
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher
    
    # اضافه کردن هندلرها
    dispatcher.add_handler(CommandHandler("start", start_handler))
    dispatcher.add_handler(CommandHandler("help", help_handler))
    dispatcher.add_handler(CommandHandler("status", status_handler))
    
    # هندلر پیام‌های متنی
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, message_handler))
    
    # هندلر دکمه‌های اینلاین
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    
    # شروع پولینگ
    updater.start_polling()
    
    logger.info("ربات شروع به کار کرد!")
    
    # منتظر ماندن تا زمانی که ربات متوقف شود
    updater.idle()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("ربات با دستور کاربر متوقف شد.")
    except Exception as e:
        logger.error(f"خطای غیرمنتظره: {e}") 