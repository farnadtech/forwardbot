import logging
from telegram import Update, ParseMode
from telegram.ext import CallbackContext
from downloader import MusicDownloader
from utils import split_into_batches, format_batch_info, format_progress_message
from keyboard import start_keyboard, create_batch_keyboard, create_cancel_keyboard, create_forward_control_keyboard, create_continue_fetching_keyboard
from config import TARGET_BOT, BATCH_SIZE
import time

# ذخیره داده‌های کاربران
user_data_store = {}

def start_handler(update: Update, context: CallbackContext):
    """دستور شروع"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    update.message.reply_text(
        f"سلام {user_name}! 👋\n\n"
        "به ربات دریافت موسیقی خوش آمدید. این ربات به شما کمک می‌کند تا موسیقی‌های موجود در کانال‌ها و گروه‌های تلگرام را به راحتی به ربات دیگری ارسال کنید.\n\n"
        "برای شروع، لطفاً از دکمه‌های زیر استفاده کنید:",
        reply_markup=start_keyboard()
    )

def help_handler(update: Update, context: CallbackContext):
    """دستور راهنما"""
    update.message.reply_text(
        "📌 *راهنمای استفاده از ربات:*\n\n"
        "1️⃣ ابتدا روی دکمه '🔍 دریافت موسیقی از کانال یا گروه' کلیک کنید.\n"
        "2️⃣ آدرس کانال یا گروه مورد نظر را وارد کنید (مثال: @channel_name یا https://t.me/channel_name).\n"
        "2️⃣(اختیاری) برای محدود کردن تعداد پیام‌های بررسی شده، یک عدد بعد از آدرس وارد کنید: @channel_name 5000\n"
        "3️⃣ ربات ابتدا 5000 پیام اول را پردازش می‌کند و سپس به شما گزینه‌ای برای ادامه دریافت می‌دهد.\n"
        "4️⃣ شما می‌توانید با انتخاب 'ادامه دریافت فایل‌های بیشتر'، 5000 پیام بعدی را دریافت کنید.\n"
        "5️⃣ در هر مرحله، فایل‌های موسیقی در دسته‌های 100 تایی مرتب می‌شوند.\n"
        "6️⃣ دسته مورد نظر را برای ارسال انتخاب کنید.\n"
        "7️⃣ فایل‌ها به ربات @remixuploadbot ارسال می‌شوند.\n\n"
        "❓ برای هرگونه سوال یا مشکل، با سازنده ربات تماس بگیرید.",
        parse_mode=ParseMode.MARKDOWN
    )

def status_handler(update: Update, context: CallbackContext):
    """نمایش وضعیت ربات"""
    user_id = update.effective_user.id
    
    if user_id in user_data_store:
        user_data = user_data_store[user_id]
        total_files = len(user_data.get("music_files", []))
        total_batches = len(user_data.get("batches", []))
        current_batch = user_data.get("current_batch", 0)
        
        status_message = (
            "📊 *وضعیت کنونی:*\n\n"
            f"🎵 تعداد کل فایل‌های موسیقی: {total_files}\n"
            f"📁 تعداد کل دسته‌ها: {total_batches}\n"
            f"📌 دسته فعلی: {current_batch}/{total_batches}\n"
        )
        
        update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN)
    else:
        update.message.reply_text("هنوز هیچ داده‌ای وجود ندارد. لطفاً ابتدا یک کانال یا گروه را اسکن کنید.")

def request_channel_handler(update: Update, context: CallbackContext):
    """درخواست آدرس کانال یا گروه"""
    update.message.reply_text(
        "لطفاً آدرس کانال یا گروه تلگرام مورد نظر را وارد کنید.\n"
        "مثال: @channel_name یا https://t.me/channel_name\n\n"
        "همچنین می‌توانید با قرار دادن عدد بعد از آدرس، تعداد پیام‌های بررسی شده را محدود کنید.\n"
        "مثال: @channel_name 5000\n"
        "اگر عدد وارد نکنید، تمام پیام‌ها بررسی خواهند شد.",
        reply_markup=create_cancel_keyboard()
    )
    
    context.user_data["waiting_for_channel"] = True

def process_channel_input(update: Update, context: CallbackContext):
    """پردازش آدرس کانال یا گروه ورودی"""
    user_id = update.effective_user.id
    user_input = update.message.text.strip()
    
    # جدا کردن آدرس کانال و محدودیت تعداد پیام‌ها (اگر وجود داشته باشد)
    parts = user_input.split()
    channel_input = parts[0]
    max_messages = None
    
    # بررسی اگر کاربر محدودیت تعداد پیام‌ها را تعیین کرده باشد
    if len(parts) > 1:
        try:
            max_messages = int(parts[1])
            if max_messages <= 0:
                update.message.reply_text("❌ تعداد پیام‌ها باید عددی مثبت باشد.")
                return
        except ValueError:
            update.message.reply_text("❌ فرمت ورودی نادرست است. لطفاً از فرمت '@channel_name [تعداد پیام‌ها]' استفاده کنید.")
            return
    
    # ارسال پیام اولیه "در حال پردازش"
    status_message = update.message.reply_text("در حال پردازش کانال... لطفاً صبر کنید. این فرآیند ممکن است چند دقیقه طول بکشد.")
    
    # ذخیره وضعیت پردازش
    context.user_data["processing_status"] = {
        "message_id": status_message.message_id,
        "last_update": time.time(),
        "processed": 0,
        "total": 0
    }
    
    # ایجاد نمونه دانلودر موسیقی
    downloader = MusicDownloader()
    downloader.connect()
    
    def update_progress(total, processed):
        """به‌روزرسانی پیشرفت دانلود"""
        now = time.time()
        status_data = context.user_data.get("processing_status", {})
        last_update = status_data.get("last_update", 0)
        
        # به‌روزرسانی پیام حداکثر هر 5 ثانیه یکبار (برای جلوگیری از فلاد)
        if now - last_update >= 5:
            progress_text = format_progress_message(total, processed)
            try:
                context.bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message.message_id,
                    text=f"در حال پردازش کانال...\n\n{progress_text}\n\nلطفاً صبر کنید. این فرآیند ممکن است چند دقیقه طول بکشد."
                )
                status_data["last_update"] = now
                status_data["processed"] = processed
                status_data["total"] = total
            except Exception as e:
                logger.error(f"خطا در به‌روزرسانی پیشرفت: {e}")
    
    # تعیین تعداد پیام‌های قابل پردازش در هر مرحله
    batch_fetch_size = 5000  # تعداد پیام‌هایی که در هر مرحله پردازش می‌شوند
    
    # اگر کاربر محدودیت تعیین نکرده، از batch_fetch_size استفاده می‌کنیم
    if max_messages is None or max_messages > batch_fetch_size:
        effective_max_messages = batch_fetch_size
    else:
        effective_max_messages = max_messages
    
    # دریافت فایل‌های موسیقی
    music_files, last_offset_id, has_more_messages = downloader.get_music_files(
        channel_input, 
        update_progress, 
        effective_max_messages
    )
    
    if not music_files:
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message.message_id,
            text="❌ هیچ فایل موسیقی در این کانال یا گروه یافت نشد یا دسترسی به آن امکان‌پذیر نیست."
        )
        downloader.disconnect()
        return
    
    # دسته‌بندی فایل‌ها
    batches = split_into_batches(music_files, BATCH_SIZE)
    
    # ذخیره اطلاعات در کانتکست کاربر
    user_data_store[user_id] = {
        "downloader": downloader,
        "channel": channel_input,
        "music_files": music_files,
        "batches": batches,
        "current_batch": 0,
        "is_forwarding": False,
        "is_paused": False,
        "last_offset_id": last_offset_id,
        "has_more_messages": has_more_messages,
        "max_messages": max_messages,  # محدودیت کلی تعیین شده توسط کاربر
        "batch_fetch_size": batch_fetch_size  # تعداد پیام‌هایی که در هر مرحله پردازش می‌شوند
    }
    
    # نمایش متن و کیبورد مناسب با توجه به وجود یا عدم وجود پیام‌های بیشتر
    batch_info = format_batch_info(batches)
    if has_more_messages:
        message_text = (
            f"✅ پردازش بخش اول کانال با موفقیت انجام شد!\n\n"
            f"🎵 تعداد فایل‌های پیدا شده: {len(music_files)}\n"
            f"📁 دسته‌بندی شده در {len(batches)} دسته\n\n"
            f"{batch_info}\n\n"
            f"⚠️ هنوز پیام‌های بیشتری در کانال وجود دارد. برای ادامه دریافت یا مشاهده دسته‌های فعلی یک گزینه را انتخاب کنید:"
        )
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message.message_id,
            text=message_text,
            reply_markup=create_continue_fetching_keyboard()
        )
    else:
        message_text = f"✅ پردازش کانال با موفقیت انجام شد!\n\n{batch_info}"
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=status_message.message_id,
            text=message_text,
            reply_markup=create_batch_keyboard(batches)
        )
    
    context.user_data["waiting_for_channel"] = False

def batch_selection_handler(update: Update, context: CallbackContext):
    """مدیریت انتخاب دسته"""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    user_data = user_data_store.get(user_id)
    
    if not user_data:
        query.edit_message_text("❌ داده‌های شما منقضی شده‌اند. لطفاً دوباره تلاش کنید.")
        return
    
    callback_data = query.data
    
    if callback_data == "cancel":
        query.edit_message_text("❌ عملیات لغو شد.")
        if "downloader" in user_data:
            user_data["downloader"].disconnect()
        user_data_store.pop(user_id, None)
        return
    
    if callback_data.startswith("batch_"):
        batch_index = int(callback_data.split("_")[1])
        user_data["current_batch"] = batch_index
        batches = user_data["batches"]
        
        if 1 <= batch_index <= len(batches):
            selected_batch = batches[batch_index - 1]
            
            query.edit_message_text(
                f"📁 دسته {batch_index} انتخاب شد. شامل {len(selected_batch)} فایل موسیقی.\n"
                "در حال آماده‌سازی برای ارسال..."
            )
            
            # ارسال اولین فایل
            user_data["is_forwarding"] = True
            user_data["is_paused"] = False
            user_data["current_file_index"] = 0
            
            forward_status_message = context.bot.send_message(
                chat_id=user_id,
                text=f"⏳ در حال ارسال فایل‌های دسته {batch_index}...\n\n"
                     f"0/{len(selected_batch)} ارسال شده",
                reply_markup=create_forward_control_keyboard(batch_index, len(batches))
            )
            
            user_data["forward_status_message"] = forward_status_message
            
            # شروع ارسال فایل‌ها
            forward_batch_files(context, user_id)

def forward_batch_files(context: CallbackContext, user_id: int):
    """ارسال فایل‌های یک دسته"""
    user_data = user_data_store.get(user_id)
    
    if not user_data or not user_data["is_forwarding"] or user_data["is_paused"]:
        return
    
    batch_index = user_data["current_batch"]
    file_index = user_data["current_file_index"]
    selected_batch = user_data["batches"][batch_index - 1]
    
    if file_index >= len(selected_batch):
        # اتمام ارسال دسته
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=user_data["forward_status_message"].message_id,
            text=f"✅ ارسال دسته {batch_index} با موفقیت انجام شد!\n\n"
                f"{len(selected_batch)}/{len(selected_batch)} فایل ارسال شده",
            reply_markup=create_forward_control_keyboard(batch_index, len(user_data["batches"]))
        )
        user_data["is_forwarding"] = False
        return
    
    # ارسال فایل بعدی
    try:
        message = selected_batch[file_index]
        success = user_data["downloader"].forward_to_bot(message, TARGET_BOT)
        
        user_data["current_file_index"] = file_index + 1
        
        # بروزرسانی پیام وضعیت
        try:
            context.bot.edit_message_text(
                chat_id=user_id,
                message_id=user_data["forward_status_message"].message_id,
                text=f"⏳ در حال ارسال فایل‌های دسته {batch_index}...\n\n"
                    f"{file_index + 1}/{len(selected_batch)} ارسال شده",
                reply_markup=create_forward_control_keyboard(batch_index, len(user_data["batches"]))
            )
        except Exception as e:
            logger.error(f"خطا در به‌روزرسانی وضعیت: {e}")
        
        # تاخیر برای جلوگیری از محدودیت فلاد
        # ادامه با فایل بعدی پس از تاخیر
        delay = 2  # تاخیر 2 ثانیه بین هر ارسال
        context.job_queue.run_once(lambda _: forward_batch_files(context, user_id), delay)
    
    except Exception as e:
        logger.error(f"خطا در ارسال فایل به ربات مقصد: {e}")
        
        # اگر با محدودیت فلاد مواجه شدیم، تاخیر بیشتری اعمال می‌کنیم
        if "RetryAfter" in str(e) or "Flood" in str(e):
            retry_time = 30  # زمان انتظار پیش‌فرض
            
            # سعی در استخراج زمان انتظار از پیام خطا
            import re
            time_match = re.search(r'(\d+(\.\d+)?)', str(e))
            if time_match:
                try:
                    retry_time = float(time_match.group(1)) + 1
                except:
                    pass
            
            logger.info(f"محدودیت فلاد اعمال شده، انتظار برای {retry_time} ثانیه...")
            
            # اطلاع‌رسانی به کاربر
            context.bot.send_message(
                chat_id=user_id,
                text=f"⚠️ محدودیت ارسال تلگرام: انتظار برای {retry_time} ثانیه قبل از ادامه ارسال..."
            )
            
            context.job_queue.run_once(lambda _: forward_batch_files(context, user_id), retry_time)
        else:
            # سایر خطاها - تلاش مجدد پس از 5 ثانیه
            context.job_queue.run_once(lambda _: forward_batch_files(context, user_id), 5)

def button_handler(update: Update, context: CallbackContext):
    """مدیریت دکمه‌های اینلاین"""
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    user_data = user_data_store.get(user_id)
    
    if not user_data:
        query.edit_message_text("❌ داده‌های شما منقضی شده‌اند. لطفاً دوباره تلاش کنید.")
        return
    
    callback_data = query.data
    
    if callback_data == "cancel":
        user_data["is_forwarding"] = False
        query.edit_message_text("❌ عملیات ارسال لغو شد.")
        if "downloader" in user_data:
            user_data["downloader"].disconnect()
        user_data_store.pop(user_id, None)
    
    elif callback_data == "pause":
        user_data["is_paused"] = True
        query.edit_message_text(
            f"⏸ ارسال فایل‌ها متوقف شد.\n\n"
            f"{user_data['current_file_index']}/{len(user_data['batches'][user_data['current_batch'] - 1])} ارسال شده",
            reply_markup=create_forward_control_keyboard(user_data["current_batch"], len(user_data["batches"]))
        )
    
    elif callback_data == "resume":
        user_data["is_paused"] = False
        query.edit_message_text(
            f"▶️ ارسال فایل‌ها از سر گرفته شد.\n\n"
            f"{user_data['current_file_index']}/{len(user_data['batches'][user_data['current_batch'] - 1])} ارسال شده",
            reply_markup=create_forward_control_keyboard(user_data["current_batch"], len(user_data["batches"]))
        )
        
        # ادامه ارسال
        context.job_queue.run_once(lambda _: forward_batch_files(context, user_id), 1)
    
    elif callback_data == "continue_fetch":
        # ادامه دریافت فایل‌های موسیقی
        query.edit_message_text("🔄 در حال ادامه دریافت فایل‌های موسیقی...\nلطفاً صبر کنید. این فرآیند ممکن است چند دقیقه طول بکشد.")
        
        # بازیابی اطلاعات کاربر
        channel_input = user_data["channel"]
        last_offset_id = user_data["last_offset_id"]
        max_messages = user_data["max_messages"]
        batch_fetch_size = user_data["batch_fetch_size"]
        current_music_files = user_data["music_files"]
        
        # تعیین محدودیت جدید
        effective_max_messages = batch_fetch_size
        if max_messages is not None:
            remaining_messages = max_messages - len(current_music_files)
            if remaining_messages <= 0:
                # اگر محدودیت تعیین شده توسط کاربر قبلاً برآورده شده
                query.edit_message_text(
                    "✅ تمام پیام‌ها در محدوده تعیین شده دریافت شده‌اند.\n\n"
                    "برای دریافت پیام‌های بیشتر، لطفاً دوباره با محدودیت جدید سعی کنید."
                )
                return
            effective_max_messages = min(batch_fetch_size, remaining_messages)
            
        # تنظیم کال‌بک پیشرفت
        status_message_id = query.message.message_id
        
        def update_progress(total, processed):
            """به‌روزرسانی پیشرفت دانلود"""
            now = time.time()
            try:
                if now - user_data.get("last_progress_update", 0) >= 5:
                    progress_text = format_progress_message(total, processed)
                    context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=status_message_id,
                        text=f"در حال ادامه دریافت فایل‌های موسیقی...\n\n{progress_text}\n\nلطفاً صبر کنید."
                    )
                    user_data["last_progress_update"] = now
            except Exception as e:
                logger.error(f"خطا در به‌روزرسانی پیشرفت: {e}")
        
        # دریافت فایل‌های موسیقی جدید
        downloader = user_data["downloader"]
        new_music_files, new_offset_id, has_more_messages = downloader.get_music_files(
            channel_input, 
            update_progress, 
            effective_max_messages, 
            last_offset_id
        )
        
        # ادغام فایل‌های جدید با قبلی
        all_music_files = current_music_files + new_music_files
        
        if not new_music_files:
            query.edit_message_text(
                "❌ هیچ فایل موسیقی جدیدی یافت نشد. احتمالاً به پایان پیام‌های کانال رسیده‌اید."
            )
            return
            
        # به‌روزرسانی دسته‌ها
        batches = split_into_batches(all_music_files, BATCH_SIZE)
        
        # ذخیره اطلاعات به‌روزشده
        user_data.update({
            "music_files": all_music_files,
            "batches": batches,
            "last_offset_id": new_offset_id,
            "has_more_messages": has_more_messages
        })
        
        # نمایش متن و کیبورد مناسب
        batch_info = format_batch_info(batches)
        if has_more_messages:
            message_text = (
                f"✅ دریافت فایل‌های جدید با موفقیت انجام شد!\n\n"
                f"🎵 تعداد کل فایل‌های پیدا شده: {len(all_music_files)}\n"
                f"🆕 تعداد فایل‌های جدید: {len(new_music_files)}\n"
                f"📁 دسته‌بندی شده در {len(batches)} دسته\n\n"
                f"{batch_info}\n\n"
                f"⚠️ هنوز پیام‌های بیشتری در کانال وجود دارد. می‌خواهید ادامه دهید؟"
            )
            query.edit_message_text(
                text=message_text,
                reply_markup=create_continue_fetching_keyboard()
            )
        else:
            message_text = (
                f"✅ دریافت همه فایل‌ها با موفقیت انجام شد!\n\n"
                f"🎵 تعداد کل فایل‌های پیدا شده: {len(all_music_files)}\n"
                f"🆕 تعداد فایل‌های جدید: {len(new_music_files)}\n"
                f"📁 دسته‌بندی شده در {len(batches)} دسته\n\n"
                f"{batch_info}"
            )
            query.edit_message_text(
                text=message_text,
                reply_markup=create_batch_keyboard(batches)
            )
    
    elif callback_data == "show_batches":
        # نمایش دسته‌ها بدون ادامه دریافت
        batch_info = format_batch_info(user_data["batches"])
        message_text = f"📂 فایل‌های دریافت شده تا کنون:\n\n{batch_info}"
        query.edit_message_text(
            text=message_text,
            reply_markup=create_batch_keyboard(user_data["batches"])
        )
    
    elif callback_data == "status":
        batch_index = user_data["current_batch"]
        file_index = user_data["current_file_index"]
        selected_batch = user_data["batches"][batch_index - 1]
        
        status_text = (
            f"📊 *وضعیت ارسال:*\n\n"
            f"📁 دسته فعلی: {batch_index}/{len(user_data['batches'])}\n"
            f"🎵 فایل‌های ارسال شده: {file_index}/{len(selected_batch)}\n"
            f"⏱ وضعیت: {'متوقف ⏸' if user_data['is_paused'] else 'در حال ارسال ▶️'}"
        )
        
        context.bot.send_message(
            chat_id=user_id,
            text=status_text,
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif callback_data.startswith("batch_"):
        # انتخاب دسته
        batch_selection_handler(update, context)

def message_handler(update: Update, context: CallbackContext):
    """مدیریت پیام‌های ورودی"""
    text = update.message.text
    
    if text == "🔍 دریافت موسیقی از کانال یا گروه":
        request_channel_handler(update, context)
    elif text == "❓ راهنما":
        help_handler(update, context)
    elif text == "📊 وضعیت":
        status_handler(update, context)
    elif context.user_data.get("waiting_for_channel"):
        process_channel_input(update, context)
    else:
        start_handler(update, context) 