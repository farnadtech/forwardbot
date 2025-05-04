from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup

def start_keyboard():
    """دکمه‌های منوی اصلی"""
    keyboard = [
        ['🔍 دریافت موسیقی از کانال یا گروه'],
        ['❓ راهنما', '📊 وضعیت']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_batch_keyboard(batches):
    """ساخت کیبورد انتخاب دسته‌ها"""
    keyboard = []
    row = []
    
    for i in range(1, len(batches) + 1):
        row.append(InlineKeyboardButton(f"دسته {i}", callback_data=f"batch_{i}"))
        
        if len(row) == 3 or i == len(batches):
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)

def create_cancel_keyboard():
    """دکمه لغو عملیات"""
    keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="cancel")]]
    return InlineKeyboardMarkup(keyboard)

def create_forward_control_keyboard(batch_index, total_batches):
    """دکمه‌های کنترل ارسال"""
    keyboard = [
        [
            InlineKeyboardButton("⏸ توقف", callback_data="pause"),
            InlineKeyboardButton("▶️ ادامه", callback_data="resume"),
            InlineKeyboardButton("❌ لغو", callback_data="cancel")
        ],
        [
            InlineKeyboardButton("📊 وضعیت", callback_data="status")
        ]
    ]
    
    if batch_index < total_batches:
        keyboard.append([InlineKeyboardButton("📁 ارسال دسته بعدی", callback_data=f"batch_{batch_index + 1}")])
    
    return InlineKeyboardMarkup(keyboard)

def create_continue_fetching_keyboard():
    """ایجاد کیبورد برای ادامه دریافت موسیقی‌ها"""
    keyboard = [
        [InlineKeyboardButton("🔄 ادامه دریافت فایل‌های بیشتر", callback_data="continue_fetch")],
        [InlineKeyboardButton("✅ پایان دریافت و نمایش دسته‌ها", callback_data="show_batches")],
        [InlineKeyboardButton("❌ لغو", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard) 