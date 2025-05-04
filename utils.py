import os
import logging
from telethon.tl.types import DocumentAttributeAudio
from config import BATCH_SIZE

# تنظیم لاگر
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def split_into_batches(items, batch_size=BATCH_SIZE):
    """تقسیم لیست به دسته‌های با اندازه مشخص"""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

def format_batch_info(batches):
    """ایجاد متن اطلاعات دسته‌های فایل موسیقی"""
    result = "📂 لیست دسته‌های موسیقی:\n\n"
    
    for i, batch in enumerate(batches, 1):
        result += f"📁 دسته {i}: شامل {len(batch)} فایل موسیقی\n"
    
    result += "\n🔍 لطفاً شماره دسته مورد نظر را برای ارسال انتخاب کنید (مثال: 1)"
    return result

def format_progress_message(total, processed):
    """نمایش پیشرفت عملیات"""
    # اگر تعداد کل نامشخص یا خیلی بزرگ باشد، فقط تعداد پردازش شده را نشان می‌دهیم
    if total > 90000:  # برای حالتی که محدودیت نداریم
        return f"🔄 در حال پردازش: {processed} پیام (بدون محدودیت)"
    
    # اطمینان از اینکه درصد بیشتر از 100 نشود
    if processed > total:
        percentage = 100.0
    else:
        percentage = (processed / total) * 100 if total > 0 else 0
    
    return f"🔄 در حال پردازش: {processed}/{total} ({percentage:.1f}%)" 