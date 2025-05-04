import logging
import asyncio
import time
from telethon import TelegramClient
from telethon.tl.functions.messages import GetHistoryRequest
from utils import logger
from telethon.tl.types import DocumentAttributeAudio, Message
from config import API_ID, API_HASH, SESSION_NAME, BOT_TOKEN, MAX_MESSAGES

class MusicDownloader:
    def __init__(self):
        """راه‌اندازی کلاینت تلگرام برای دانلود موسیقی"""
        self.client = None
        self.is_connected = False
        self.loop = None
        self.user_mode = True  # استفاده از حساب کاربری عادی به جای ربات
        
    def connect(self):
        """ایجاد اتصال به تلگرام"""
        if not self.is_connected:
            try:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
                
                # استفاده از نام session برای احراز هویت
                self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH, loop=self.loop)
                
                if self.user_mode:
                    # حالت کاربر عادی: تلاش برای استفاده از session موجود
                    logger.info("تلاش برای اتصال با حساب کاربری عادی...")
                    
                    async def _connect_and_check():
                        await self.client.connect()
                        return await self.client.is_user_authorized()
                    
                    self.loop.run_until_complete(self.client.connect())
                    if not self.loop.run_until_complete(self.client.is_user_authorized()):
                        # اگر قبلاً احراز هویت نشده، نیاز به ورود ماژول interactive_auth است
                        logger.error("سشن معتبر یافت نشد. لطفاً ابتدا با اجرای اسکریپت auth_user.py به صورت تعاملی احراز هویت کنید.")
                        return False
                    
                    logger.info("اتصال با حساب کاربری عادی با موفقیت انجام شد.")
                else:
                    # حالت ربات: تلاش برای استفاده از توکن ربات
                    try:
                        logger.info("تلاش برای اتصال با Bot Token...")
                        
                        async def _start_bot():
                            await self.client.start(bot_token=BOT_TOKEN)
                        
                        self.loop.run_until_complete(_start_bot())
                        logger.info("اتصال با Bot Token با موفقیت انجام شد.")
                    except Exception as e:
                        logger.error(f"خطا در اتصال با Bot Token: {e}")
                        return False
                
                self.is_connected = True
                logger.info("اتصال به تلگرام برقرار شد")
                return True
            except Exception as e:
                logger.error(f"خطا در برقراری اتصال به تلگرام: {e}")
                return False
                
    def disconnect(self):
        """قطع اتصال از تلگرام"""
        if self.is_connected and self.client:
            try:
                async def _disconnect():
                    await self.client.disconnect()
                
                self.loop.run_until_complete(_disconnect())
                self.is_connected = False
                logger.info("اتصال به تلگرام قطع شد")
            except Exception as e:
                logger.error(f"خطا در قطع اتصال از تلگرام: {e}")
    
    def get_entity(self, chat_id):
        """دریافت اطلاعات کانال یا گروه"""
        try:
            async def _get_entity():
                return await self.client.get_entity(chat_id)
                
            entity = self.loop.run_until_complete(_get_entity())
            return entity
        except Exception as e:
            logger.error(f"خطا در دریافت اطلاعات کانال یا گروه: {e}")
            return None
    
    def get_music_files(self, chat_id, progress_callback=None, max_messages=None, start_offset_id=0):
        """دریافت همه فایل‌های موسیقی از کانال یا گروه
        
        Args:
            chat_id: آدرس کانال یا گروه
            progress_callback: تابع کال‌بک برای نمایش پیشرفت
            max_messages: حداکثر تعداد پیام‌های قابل پردازش
            start_offset_id: شناسه پیامی که پردازش از آن شروع می‌شود
            
        Returns:
            tuple: (فایل‌های موسیقی, آخرین offset_id, آیا پیام‌های بیشتری وجود دارد)
        """
        if not self.is_connected:
            if not self.connect():
                return [], 0, False
        
        entity = self.get_entity(chat_id)
        if not entity:
            return [], 0, False
        
        music_files = []
        offset_id = start_offset_id  # اضافه کردن امکان شروع از یک پیام خاص
        limit = 100
        # استفاده از مقدار ورودی کاربر برای تعیین محدودیت
        messages_limit = max_messages  # اگر None باشد، یعنی محدودیتی نداریم
        total_count = 100000  # یک مقدار بزرگ برای نمایش پیشرفت در حالت بدون محدودیت
        if messages_limit:
            total_count = messages_limit  # اگر محدودیت داریم، از آن استفاده می‌کنیم
        processed = 0    # تعداد پیام‌های پردازش شده
        has_more_messages = False  # آیا پیام‌های بیشتری وجود دارد؟
        
        # ابتدا سعی می‌کنیم تعداد تقریبی پیام‌ها را بدست آوریم
        try:
            # روش ساده‌تر برای برآورد تعداد پیام‌ها
            logger.info(f"در حال محاسبه تعداد تقریبی پیام‌های کانال/گروه...")
            
            # محدودیت تعداد پیام‌ها (اگر تعیین شده باشد)
            if messages_limit:
                logger.info(f"محدود کردن تعداد پیام‌های قابل پردازش به {messages_limit}")
            else:
                logger.info("🔄 بدون محدودیت: تمام پیام‌های کانال بررسی خواهند شد (این فرآیند ممکن است طولانی باشد)")
                
        except Exception as e:
            logger.error(f"خطا در دریافت تعداد پیام‌ها: {e}")
        
        async def get_messages():
            nonlocal offset_id, music_files, processed, has_more_messages
            retry_count = 0
            
            while True:
                # بررسی برای توقف پردازش پس از رسیدن به حداکثر تعداد پیام‌ها (اگر تعیین شده باشد)
                if messages_limit and processed >= messages_limit:
                    logger.info(f"رسیدن به حداکثر تعداد پیام‌های قابل پردازش ({messages_limit})")
                    has_more_messages = True  # مشخص می‌کنیم که هنوز پیام‌های بیشتری وجود دارد
                    break
                
                try:
                    # افزودن تاخیر بین درخواست‌ها برای جلوگیری از فلاد کنترل
                    await asyncio.sleep(0.5)
                    
                    # اطلاع‌رسانی پیشرفت
                    if progress_callback and processed % 20 == 0:
                        progress_callback(total_count, processed)
                    
                    history = await self.client(GetHistoryRequest(
                        peer=entity,
                        offset_id=offset_id,
                        offset_date=None,
                        add_offset=0,
                        limit=limit,
                        max_id=0,
                        min_id=0,
                        hash=0
                    ))
                    
                    if not history.messages:
                        logger.info("پایان پیام‌های کانال")
                        has_more_messages = False
                        break
                        
                    messages = history.messages
                    batch_size = len(messages)
                    audio_count_in_batch = 0
                    
                    logger.info(f"دریافت {batch_size} پیام جدید (مجموع پردازش شده: {processed})")
                    
                    for message in messages:
                        processed += 1
                        
                        # تشخیص دقیق‌تر فایل‌های صوتی
                        is_audio = await self.is_audio_message_async(message)
                        if is_audio:
                            audio_count_in_batch += 1
                            music_files.append(message)
                        
                        # به‌روزرسانی پیشرفت با هر 10 پیام
                        if processed % 10 == 0 and progress_callback:
                            progress_callback(total_count, processed)
                        
                        # بررسی برای توقف پردازش در داخل حلقه (اگر تعیین شده باشد)
                        if messages_limit and processed >= messages_limit:
                            logger.info(f"رسیدن به حداکثر تعداد پیام در حلقه داخلی ({messages_limit})")
                            has_more_messages = True  # مشخص می‌کنیم که هنوز پیام‌های بیشتری وجود دارد
                            break
                    
                    logger.info(f"یافتن {audio_count_in_batch} فایل صوتی در این دسته (مجموع: {len(music_files)})")
                    
                    if not messages:
                        logger.info("پایان پیام‌ها")
                        break
                        
                    offset_id = messages[-1].id
                    
                    if len(messages) < limit:
                        logger.info("تعداد پیام‌های دریافتی کمتر از حد مجاز - پایان دریافت")
                        break
                    
                    # استراحت کوتاه بین دسته‌ها
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    retry_count += 1
                    logger.error(f"خطا در دریافت پیام‌ها: {e}")
                    
                    # تلاش مجدد با تاخیر بیشتر
                    wait_time = min(30, retry_count * 5)
                    logger.info(f"انتظار برای {wait_time} ثانیه قبل از تلاش مجدد...")
                    await asyncio.sleep(wait_time)
                    
                    # پس از چند تلاش ناموفق، خروج
                    if retry_count >= 10:  # افزایش تعداد تلاش‌ها
                        logger.error("تعداد تلاش‌های ناموفق بیش از حد مجاز - توقف پردازش")
                        break
                    
        self.loop.run_until_complete(get_messages())
        
        if len(music_files) == 0:
            logger.warning("هیچ فایل موسیقی در این کانال یافت نشد!")
        else:
            logger.info(f"تعداد {len(music_files)} فایل موسیقی یافت شد")
            
        return music_files, offset_id, has_more_messages
    
    def is_audio_message(self, message):
        """بررسی می‌کند که آیا پیام شامل فایل صوتی است یا خیر (sync)"""
        return self.loop.run_until_complete(self.is_audio_message_async(message))
    
    async def is_audio_message_async(self, message):
        """بررسی می‌کند که آیا پیام شامل فایل موسیقی است یا خیر (async)
        توجه: این تابع فقط فایل‌های موسیقی واقعی را تشخیص می‌دهد و پیام‌های صوتی (voice) را نادیده می‌گیرد."""
        if not isinstance(message, Message):
            return False
            
        # بررسی فایل‌های موسیقی مستقیم
        if hasattr(message, 'audio') and message.audio:
            return True
            
        # پیام‌های صوتی (voice) را نادیده می‌گیریم
        if hasattr(message, 'voice') and message.voice:
            return False
            
        # بررسی سایر فایل‌ها برای ویژگی‌های صوتی
        if hasattr(message, 'document') and message.document:
            for attribute in message.document.attributes:
                if isinstance(attribute, DocumentAttributeAudio):
                    # فقط اگر voice نباشد آن را به عنوان موسیقی در نظر می‌گیریم
                    if not getattr(attribute, 'voice', False):
                        return True
                    
        # بررسی media
        if hasattr(message, 'media'):
            media = message.media
            if hasattr(media, 'document'):
                for attribute in media.document.attributes:
                    if isinstance(attribute, DocumentAttributeAudio):
                        # فقط اگر voice نباشد آن را به عنوان موسیقی در نظر می‌گیریم
                        if not getattr(attribute, 'voice', False):
                            return True
                        
        return False
        
    def forward_to_bot(self, message, target_bot):
        """ارسال یک پیام به ربات دیگر"""
        if not self.is_connected:
            if not self.connect():
                return False
        
        try:
            async def _forward_message():
                await self.client.forward_messages(target_bot, message)
                
            self.loop.run_until_complete(_forward_message())
            return True
        except Exception as e:
            logger.error(f"خطا در ارسال پیام به ربات هدف: {e}")
            return False 