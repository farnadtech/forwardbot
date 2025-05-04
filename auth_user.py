#!/usr/bin/env python3
"""
این اسکریپت برای احراز هویت حساب کاربری تلگرام و ایجاد فایل session استفاده می‌شود.
اجرای این اسکریپت به صورت تعاملی است و نیاز به ورود شماره تلفن و کد تأیید دارد.
"""

import os
import sys
import asyncio
import shutil
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import API_ID, API_HASH, SESSION_NAME

# استفاده از نام سشن متفاوت برای جلوگیری از تداخل با سرویس در حال اجرا
TEMP_SESSION_NAME = f"{SESSION_NAME}_auth_temp"

async def main():
    print("ابزار احراز هویت تلگرام")
    print("=" * 30)
    
    # بررسی تنظیمات API
    if not API_ID or not API_HASH:
        print("خطا: API_ID و API_HASH در فایل config.py یا .env تنظیم نشده‌اند.")
        print("لطفاً ابتدا این مقادیر را تنظیم کنید.")
        return
    
    # ایجاد سشن تلگرام با نام موقت
    print(f"در حال ایجاد سشن موقت...")
    client = TelegramClient(TEMP_SESSION_NAME, API_ID, API_HASH)
    
    try:
        await client.connect()
        
        # بررسی وضعیت احراز هویت
        if await client.is_user_authorized():
            print("سشن موقت قبلاً احراز هویت شده است!")
            me = await client.get_me()
            print(f"حساب کاربری: {me.username if me.username else me.phone}")
        else:
            # درخواست شماره تلفن
            phone = input("لطفاً شماره تلفن خود را با کد کشور وارد کنید (مثال: +989123456789): ")
            print("در حال ارسال کد تأیید...")
            await client.send_code_request(phone)
            
            # درخواست کد تأیید
            code = input("کد تأیید ارسال شده را وارد کنید: ")
            try:
                await client.sign_in(phone, code)
                print("احراز هویت با موفقیت انجام شد!")
                
                # نمایش اطلاعات کاربر
                me = await client.get_me()
                print(f"حساب کاربری: {me.username if me.username else me.phone}")
            except SessionPasswordNeededError:
                # در صورت نیاز به رمز عبور دو مرحله‌ای
                password = input("رمز عبور تأیید دو مرحله‌ای را وارد کنید: ")
                await client.sign_in(password=password)
                print("احراز هویت با موفقیت انجام شد!")
                
                # نمایش اطلاعات کاربر
                me = await client.get_me()
                print(f"حساب کاربری: {me.username if me.username else me.phone}")
    except Exception as e:
        print(f"خطا در احراز هویت: {e}")
        return
    finally:
        # قطع اتصال
        await client.disconnect()
    
    # کپی سشن موقت به سشن اصلی
    try:
        # اطمینان از اینکه فایل سشن موقت ایجاد شده است
        temp_session_file = f"{TEMP_SESSION_NAME}.session"
        target_session_file = f"{SESSION_NAME}.session"
        
        if os.path.exists(temp_session_file):
            print(f"\nکپی فایل سشن موقت به سشن اصلی...")
            
            # حذف فایل سشن اصلی قبلی اگر وجود داشته باشد
            if os.path.exists(target_session_file):
                os.remove(target_session_file)
            
            # کپی فایل سشن موقت به سشن اصلی
            shutil.copy2(temp_session_file, target_session_file)
            print("فایل سشن با موفقیت کپی شد.")
            
            # تنظیم مجوزهای فایل
            os.chmod(target_session_file, 0o600)
            
            # حذف فایل سشن موقت
            os.remove(temp_session_file)
            print("فایل سشن موقت حذف شد.")
            
            print(f"اکنون می‌توانید ربات را اجرا کنید.")
            print(f"مسیر فایل سشن نهایی: {target_session_file}")
        else:
            print("خطا: فایل سشن موقت ایجاد نشد.")
    except Exception as e:
        print(f"خطا در کپی فایل سشن: {e}")

if __name__ == "__main__":
    # اجرای اسکریپت در حلقه رویداد
    asyncio.run(main()) 