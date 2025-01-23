import os
import logging
import sqlite3
import asyncio
from datetime import datetime
import google.generativeai as genai
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
    MessageHandler,
    filters,
    ConversationHandler,
)

# تنظیمات API
GOOGLE_API_KEY = 'AIzaSyC53b7n-px8gnM7-govA1LMDMY0Qr7Qzr4'
TOKEN = "7434501070:AAFuuTwyLg0T4oENbAvMgspW3YEyMlgYSjg"
ADMINS = [6894055351]

# حالت‌های مکالمه
SMART_CHAT, END_CHAT, ADMIN_PANEL = range(3)

# تنظیمات دوره‌های آموزشی
COURSES = {
    'signals': {
        'folder': 'signals',
        'name': 'سیگنال‌ها و سیستم‌ها',
        'drive_link': 'https://drive.google.com/drive/folders/1qtsdaBt-tmNruB45o7pKHSKIMxyZS2mC?usp=sharing'
    },
    'comm_circuits': {
        'folder': 'circuits',
        'name': 'مدارهای مخابراتی',
        'drive_link': 'https://drive.google.com/drive/folders/1YpsQwMb-Seju7Q3cgkI9QTDrxiOmdiGQ?usp=sharing'
    },
    'dsp': {
        'folder': 'dsp',
        'name': 'پردازش سیگنال دیجیتال',
        'drive_link': 'https://drive.google.com/drive/folders/1qtsdaBt-tmNruB45o7pKHSKIMxyZS2mC?usp=sharing'
    },
    'adv_dsp': {
        'folder': 'adv_dsp',
        'name': 'پردازش پیشرفته سیگنال دیجیتال',
        'drive_link': 'https://drive.google.com/drive/folders/1YpsQwMb-Seju7Q3cgkI9QTDrxiOmdiGQ?usp=sharing'
    }
}

# اطلاعات تماس و دانشگاهی
CONTACT_INFO = """📞 اطلاعات تماس:
➖➖➖➖➖➖
📱 تلفن: 09394959842
📧 ایمیل: ghimatgar@pgu.ac.ir
تلگرام: @Hgh9816
➖➖➖➖➖➖"""

UNIVERSITY_INFO = """🎓 دانشگاه خلیج فارس - دانشکده سیستم های هوشمند و علوم داده 
📚 رشته‌های مرتبط:
- کارشناسی ارشد مهندسی برق-مخابرات
- دکتری تخصصی پردازش سیگنال
🏫 امکانات آموزشی:
- آزمایشگاه پیشرفته DSP
- شبیه‌سازهای مخابراتی"""

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# پیکربندی Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

# --- دیتابیس ---
def init_db():
    conn = sqlite3.connect('bot_users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, 
                  username TEXT,
                  first_name TEXT,
                  last_name TEXT,
                  join_date TEXT,
                  message_count INTEGER DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS broadcasts
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  message TEXT,
                  sent_date TEXT,
                  success_count INTEGER,
                  fail_count INTEGER)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  message TEXT NOT NULL,
                  sender TEXT NOT NULL,
                  timestamp TEXT)''')
    
    conn.commit()
    conn.close()

init_db()

class Database:
    @staticmethod
    def add_user(user_data: dict):
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('''INSERT OR IGNORE INTO users 
                     (user_id, username, first_name, last_name, join_date)
                     VALUES (?, ?, ?, ?, ?)''',
                  (user_data['id'], user_data.get('username'), 
                   user_data.get('first_name'), user_data.get('last_name'),
                   datetime.now().isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_all_users():
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('SELECT user_id FROM users')
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users

    @staticmethod
    def get_stats():
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM users')
        total_users = c.fetchone()[0]
        c.execute('SELECT SUM(message_count) FROM users')
        total_messages = c.fetchone()[0] or 0
        conn.close()
        return total_users, total_messages

    @staticmethod
    def log_broadcast(msg: str, success: int, fail: int):
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('''INSERT INTO broadcasts 
                     (message, sent_date, success_count, fail_count)
                     VALUES (?, ?, ?, ?)''',
                  (msg, datetime.now().isoformat(), success, fail))
        conn.commit()
        conn.close()

    @staticmethod
    def add_chat_message(user_id: int, message: str, sender: str):
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('''INSERT INTO chats 
                    (user_id, message, sender, timestamp)
                    VALUES (?, ?, ?, ?)''',
                (user_id, message, sender, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    @staticmethod
    def get_chat_users():
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('SELECT DISTINCT user_id FROM chats')
        users = [row[0] for row in c.fetchall()]
        conn.close()
        return users

    @staticmethod
    def get_user_chats(user_id: int):
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('''SELECT message, sender, timestamp 
                   FROM chats WHERE user_id = ? 
                   ORDER BY timestamp''', (user_id,))
        chats = c.fetchall()
        conn.close()
        return chats

# --- شخصیت پردازی ---
class ProfessorPersonality:
    PROFILE = """نام: دکتر حجت قیمتگر
سمت: استاد یار دانشگاه خلیج فارس
تخصص: مهندسی برق-مخابرات 
ویژگی‌های شخصیتی:
- جدی و حرفه‌ای در محیط آموزشی
- شوخ‌طبعی محدود و علمی
"""

    HUMOR_TRIGGERS = {
        "ممنون": "خوشحالم که مفید بود! حالا بریم سراغ مسائل جذاب‌تر...",
        "سخت": "اگر این رو سخت میبینید، حضوری مراجعه کنید تا توضیح دهم!",
        "مثال": "مثل این میمونه که... (همیشه مثال‌ها مخابراتی هستند!)",
        "خسته": "خستگی در کار دانشجویی مجاز نیست! قهوه بنوشید و ادامه دهید!"
    }

    @classmethod
    def add_humor(cls, response: str) -> str:
        for trigger, joke in cls.HUMOR_TRIGGERS.items():
            if trigger in response.lower():
                return f"{response}\n\n💡 {joke}"
        return response

# --- هوش مصنوعی ---
class GoogleAIChat:
    @staticmethod
    async def generate_response(prompt: str) -> str:
        try:
            response = model.generate_content(
                f"شما در نقش دکتر حجت قیمتگر عمل می‌کنید. با مشخصات زیر پاسخ دهید:\n"
                f"{ProfessorPersonality.PROFILE}\n\n"
                f"سوال: {prompt}\n"
                "پاسخ باید دارای این ویژگی‌ها باشد:\n"
                "- استفاده از اصطلاحات تخصصی به اندازه لازم\n"
                "- ساختار علمی و دانشگاهی\n"
                "- حداکثر 10% شوخ‌طبعی حرفه‌ای\n"
                "- ارجاع به منابع درسی معتبر\n"
                "- پاسخ ها زیاد طولانی نباشد\n",
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'block_none',
                    'HARM_CATEGORY_HATE_SPEECH': 'block_none',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'block_none',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'block_none'
                },
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1500,
                    temperature=0.85,
                    top_p=0.95
                )
            )
            return ProfessorPersonality.add_humor(f"👨🏫 دکتر قیمتگر:\n\n{response.text}")
            
        except Exception as e:
            logger.error(f"خطای Gemini API: {str(e)}")
            return "⚠️ خطا در پردازش سوال. لطفا مجددا تلاش کنید"

# --- دستورات کاربری ---
async def start(update: Update, context: CallbackContext):
    try:
        context.user_data.clear()
        user = update.effective_user
        Database.add_user({
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        })
        
        keyboard = [
            [InlineKeyboardButton("📡 " + COURSES['signals']['name'], callback_data='signals')],
            [InlineKeyboardButton("📶 " + COURSES['comm_circuits']['name'], callback_data='comm_circuits')],
            [InlineKeyboardButton("🎛 " + COURSES['dsp']['name'], callback_data='dsp')],
            [InlineKeyboardButton("🚀 " + COURSES['adv_dsp']['name'], callback_data='adv_dsp')],
            [InlineKeyboardButton("💬 چت باهوش مصنوعی من", callback_data='smart_chat')],
            [InlineKeyboardButton("📞 ارتباط با من", callback_data='contact')]
        ]
        
        if user.id in ADMINS:
            keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data='admin_panel')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await (update.callback_query.edit_message_text if update.callback_query 
               else update.message.reply_text)(
            f'👨🏫 به ربات آموزشی دکتر حجت قیمتگر خوش آمدید!\n{UNIVERSITY_INFO}\n'
            'لطفاً گزینه مورد نظر را انتخاب کنید:',
            reply_markup=reply_markup
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"خطا در شروع: {e}")
        await handle_error(update, context)
        return ConversationHandler.END
    
async def admin_panel(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMINS:
        await query.answer("⚠️ دسترسی غیرمجاز!", show_alert=True)
        return

    keyboard = [
        [InlineKeyboardButton("📊 آمار کاربران", callback_data='stats')],
        [InlineKeyboardButton("📣 ارسال همگانی", callback_data='broadcast')],
        [InlineKeyboardButton("💬 چت کاربران", callback_data='user_chats')],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        "🔧 پنل مدیریت:\n\nلطفا گزینه مورد نظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PANEL

async def handle_admin_actions(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    if query.from_user.id not in ADMINS:
        await query.answer("⚠️ دسترسی غیرمجاز!", show_alert=True)
        return

    if query.data == 'stats':
        total_users, total_messages = Database.get_stats()
        await query.edit_message_text(
            f"📊 آمار واقعی سیستم:\n\n👥 کاربران فعال: {total_users}\n💬 کل پیام‌های ارسالی: {total_messages}\n📅 آخرین بروزرسانی: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')]])
        )
    elif query.data == 'broadcast':
        await query.edit_message_text(
            "لطفا پیام همگانی را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("لغو", callback_data='admin_panel')]])
        )
        return ADMIN_PANEL

async def handle_broadcast(update: Update, context: CallbackContext):
    if update.message.from_user.id not in ADMINS:
        return
    
    context.user_data['broadcast_msg'] = update.message.text
    
    keyboard = [
        [InlineKeyboardButton("✅ تایید و ارسال", callback_data='confirm_broadcast')],
        [InlineKeyboardButton("❌ لغو", callback_data='admin_panel')]
    ]
    
    await update.message.reply_text(
        f"📣 پیام همگانی:\n\n{update.message.text}\n\nآیا مطمئن هستید؟",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PANEL

async def confirm_broadcast(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    msg = context.user_data.get('broadcast_msg', '')
    users = Database.get_all_users()
    
    success = 0
    fail = 0
    
    await query.edit_message_text("⏳ در حال ارسال پیام به کاربران...")
    
    for user_id in users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📣 پیام همگانی:\n\n{msg}"
            )
            success += 1
        except Exception as e:
            logger.error(f"خطا در ارسال به {user_id}: {str(e)}")
            fail += 1
        await asyncio.sleep(0.1)
    
    Database.log_broadcast(msg, success, fail)
    
    await query.edit_message_text(
        f"✅ ارسال همگانی تکمیل شد!\n\n✅ موفق: {success}\n❌ ناموفق: {fail}"
    )
    return ConversationHandler.END

async def start_smart_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💬 لطفا سوال خود را بپرسید:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data='end_chat')]])
    )
    return SMART_CHAT

async def end_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    if query:
        await query.answer()
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

async def show_contact(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        CONTACT_INFO,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
        )
    )

async def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⚠️ خطای سیستمی رخ داد. لطفا مجددا تلاش کنید"
    )

async def handle_error(update: Update, context: CallbackContext):
    await error_handler(update, context)

async def show_download_options(update: Update, context: CallbackContext, course_type: str):
    query = update.callback_query
    await query.answer()
    
    course = COURSES[course_type]
    keyboard = [
        [
            InlineKeyboardButton("📁 دانلود مستقیم", callback_data=f'direct_{course_type}'),
            InlineKeyboardButton("🔗 لینک گوگل درایو", callback_data=f'link_{course_type}')
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
    ]
    
    await query.edit_message_text(
        f"📚 {course['name']}\n\nلطفا روش دریافت فایل‌ها را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_course_files(update: Update, context: CallbackContext, course_type: str):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    course = COURSES[course_type]
    
    back_button = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    
    try:
        pdf_files = sorted(
            [f for f in os.listdir(course['folder']) if f.endswith('.pdf')],
            key=lambda x: os.path.getctime(os.path.join(course['folder'], x))
        )
        
        if not pdf_files:
            await query.edit_message_text(f"⚠️ فایلی برای {course['name']} یافت نشد!", reply_markup=InlineKeyboardMarkup(back_button))
            return

        total_files = len(pdf_files)
        main_status = await query.edit_message_text(f"🔄 آپلود {course['name']}...")

        for index, pdf in enumerate(pdf_files, 1):
            try:
                status_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏳ در حال آپلود فایل {index}/{total_files}..."
                )
                
                file_path = os.path.join(course['folder'], pdf)
                with open(file_path, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(file, filename=f"{course['name']}_{index}.pdf"),
                        caption=f"📚 {course['name']} - فایل {index}"
                    )
                
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
                
            except Exception as e:
                logger.error(f"خطا در آپلود {pdf}: {e}")
                await main_status.edit_text(
                    f"⚠️ خطا در آپلود فایل {index}!",
                    reply_markup=InlineKeyboardMarkup(back_button)
                )
                return

        await context.bot.delete_message(chat_id=chat_id, message_id=main_status.message_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ فایل‌های {course['name']} با موفقیت آپلود شدند!",
            reply_markup=InlineKeyboardMarkup(back_button)
        )

    except Exception as e:
        logger.error(f"خطای کلی: {e}")
        await handle_error(update, context)

async def send_drive_link(update: Update, context: CallbackContext, course_type: str):
    query = update.callback_query
    await query.answer()
    
    course = COURSES[course_type]
    
    await query.edit_message_text(
        f"🔗 لینک گوگل درایو برای {course['name']}:\n\n{course['drive_link']}\n\n➖➖➖➖➖➖",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
        )
    )

async def handle_chat_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    user_id = update.effective_user.id
    
    # Save user message
    Database.add_chat_message(user_id, user_message, 'user')
    
    try:
        conn = sqlite3.connect('bot_users.db')
        c = conn.cursor()
        c.execute('UPDATE users SET message_count = message_count + 1 WHERE user_id = ?',
                  (user_id,))
        conn.commit()
        conn.close()
        
        await context.bot.send_chat_action(update.effective_chat.id, "typing")
        response = await GoogleAIChat.generate_response(user_message)
        
        # Save bot response
        Database.add_chat_message(user_id, response, 'bot')
        
        await update.message.reply_text(
            response,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پایان چت", callback_data='end_chat')]])
        )
        
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")
        await update.message.reply_text("⚠️ خطایی در پردازش سوال رخ داد!")
    
    return SMART_CHAT

async def show_chat_users(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    users = Database.get_chat_users()
    if not users:
        await query.edit_message_text("هنوز هیچ چتی ثبت نشده است.")
        return ADMIN_PANEL
    
    keyboard = []
    for user_id in users:
        keyboard.append([InlineKeyboardButton(f"👤 کاربر {user_id}", callback_data=f'view_chat_{user_id}')])
    
    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data='admin_panel')])
    
    await query.edit_message_text(
        "لیست کاربران با چت‌های ذخیره شده:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ADMIN_PANEL

async def show_user_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    user_id = int(query.data.split('_')[2])
    chats = Database.get_user_chats(user_id)
    
    chat_history = "📜 تاریخچه چت کاربر:\n\n"
    for msg in chats:
        sender = "کاربر" if msg[1] == 'user' else "ربات"
        time = datetime.fromisoformat(msg[2]).strftime("%Y-%m-%d %H:%M")
        chat_history += f"⏰ {time}\n🎭 {sender}:\n{msg[0]}\n\n"
    
    # Split long messages
    if len(chat_history) > 4096:
        parts = [chat_history[i:i+4096] for i in range(0, len(chat_history), 4096)]
        for part in parts:
            await query.message.reply_text(part)
    else:
        await query.edit_message_text(chat_history)
    
    await query.message.reply_text(
        "🔙",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("بازگشت به لیست چت‌ها", callback_data='user_chats')]]
        )
    )
    return ADMIN_PANEL

async def button_click(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'contact':
            await show_contact(update, context)
        elif query.data == 'admin_panel':
            await admin_panel(update, context)
        elif query.data.startswith('direct_'):
            _, course_type = query.data.split('_', 1)
            await send_course_files(update, context, course_type)
        elif query.data.startswith('link_'):
            _, course_type = query.data.split('_', 1)
            await send_drive_link(update, context, course_type)
        elif query.data in COURSES:
            await show_download_options(update, context, query.data)
        elif query.data == 'back_to_main':
            await start(update, context)
        elif query.data == 'end_chat':
            await end_chat(update, context)
        elif query.data == 'user_chats':
            await show_chat_users(update, context)
        elif query.data.startswith('view_chat_'):
            await show_user_chat(update, context)
        else:
            await query.edit_message_text(text="🔄 این بخش به زودی اضافه خواهد شد")
            
    except Exception as e:
        logger.error(f"خطای کلی: {str(e)}")
        await handle_error(update, context)

def main():
    print("✅ Dr. Gheymatgar's educational bot is now active!")
    
    for course in COURSES.values():
        os.makedirs(course['folder'], exist_ok=True)
        print(f"📂 The folder {course['folder']} has been created/verified")
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_smart_chat, pattern='^smart_chat$'),
            CallbackQueryHandler(admin_panel, pattern='^admin_panel$')
        ],
        states={
            SMART_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message),
                CallbackQueryHandler(end_chat, pattern='^end_chat$')
            ],
            ADMIN_PANEL: [
                CallbackQueryHandler(handle_admin_actions, pattern='^(stats|broadcast)$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast),
                CallbackQueryHandler(confirm_broadcast, pattern='^confirm_broadcast$'),
                CallbackQueryHandler(show_chat_users, pattern='^user_chats$'),
                CallbackQueryHandler(show_user_chat, pattern='^view_chat_')
            ]
        },
        fallbacks=[
            CommandHandler('start', start),
            CallbackQueryHandler(start, pattern='^back_to_main$')
        ]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()