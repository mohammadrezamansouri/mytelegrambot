import os
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    CallbackContext,
)

TOKEN = "7434501070:AAFuuTwyLg0T4oENbAvMgspW3YEyMlgYSjg"



COURSES = {
    'dsp': {
        'folder': 'dsp',
        'name': 'پردازش سیگنال دیجیتال',
        'drive_link': 'https://drive.google.com/drive/folders/1qtsdaBt-tmNruB45o7pKHSKIMxyZS2mC?usp=sharing'
    },
    'adv_dsp': {
        'folder': 'adsp',
        'name': 'پردازش سیگنال های دیجیتال پیشرفته',
        'drive_link': 'https://drive.google.com/drive/folders/1YpsQwMb-Seju7Q3cgkI9QTDrxiOmdiGQ?usp=sharing'
    },
    'comm_circuit': {
        'folder': 'medar',
        'name': 'مدار مخابراتی',
        'drive_link': 'YOUR_GOOGLE_DRIVE_LINK_HERE'
    }
}



CONTACT_INFO = """
📞 اطلاعات تماس:

➖➖➖➖➖➖
📱 تلفن: 
09394959842

📧 پست الکترونیکی: 
ghimatgar@pgu.ac.ir
➖➖➖➖➖➖
"""





logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: CallbackContext):
    try:
        keyboard = [
            [InlineKeyboardButton("📡 " + COURSES['dsp']['name'], callback_data='dsp')],
            [InlineKeyboardButton("🎛 " + COURSES['adv_dsp']['name'], callback_data='adv_dsp')],
            [InlineKeyboardButton("📶 " + COURSES['comm_circuit']['name'], callback_data='comm_circuit')],
            [InlineKeyboardButton("📞 ارتباط با من", callback_data='contact')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                '👨🏫 به ربات آموزشی دکتر قیمتگر خوش آمدید!\n'
                'لطفا گزینه مورد نظر را انتخاب کنید:',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                '👨🏫 به ربات آموزشی دکتر قیمتگر خوش آمدید!\n'
                'لطفا گزینه مورد نظر را انتخاب کنید:',
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"خطا در شروع: {e}")
        await handle_error(update, context)

async def show_download_options(update: Update, context: CallbackContext, course_type: str):
    query = update.callback_query
    await query.answer()
    
    course = COURSES[course_type]
    keyboard = [
        [
            InlineKeyboardButton("📥 دریافت مستقیم در تلگرام", callback_data=f"direct_{course_type}"),
            InlineKeyboardButton("🌐 دریافت از گوگل درایو", callback_data=f"link_{course_type}")
        ],
        [InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_main')]
    ]
    
    try:
        await query.edit_message_text(
            f"📚 {course['name']}\n"
            "لطفا روش دریافت را انتخاب کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطا در نمایش گزینه‌ها: {e}")
        await handle_error(update, context)

async def send_course_files(update: Update, context: CallbackContext, course_type: str):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    course = COURSES[course_type]
    
    back_button = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_main')]]
    
    try:
        pdf_files = sorted(
            [f for f in os.listdir(course['folder']) if f.endswith('.pdf')],
            key=lambda x: os.path.getctime(os.path.join(course['folder'], x))
        )
        
        if not pdf_files:
            await query.edit_message_text(f"⚠️ فایلی برای {course['name']} یافت نشد!", reply_markup=InlineKeyboardMarkup(back_button))
            return

        total_files = len(pdf_files)
        main_status = await query.edit_message_text(f"🔄 در حال آغاز آپلود {course['name']}...")

        for index, pdf in enumerate(pdf_files, 1):
            try:
                status_msg = await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"⏳ در حال آپلود فایل شماره {index}/{total_files}..."
                )
                
                file_path = os.path.join(course['folder'], pdf)
                with open(file_path, 'rb') as file:
                    await context.bot.send_document(
                        chat_id=chat_id,
                        document=InputFile(file, filename=f"{course['name']}_{index}.pdf"),
                        caption=f"📚 {course['name']} - فایل شماره {index}",
                        read_timeout=30,
                        write_timeout=30,
                        connect_timeout=30
                    )
                
                await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
                
            except Exception as e:
                logger.error(f"خطا در آپلود فایل {pdf}: {e}")
                await main_status.edit_text(
                    f"⚠️ خطا در آپلود فایل شماره {index}!",
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
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_main')]]
    
    try:
        await query.edit_message_text(
            f"🔗 لینک گوگل درایو برای {course['name']}:\n"
            f"{course['drive_link']}\n\n"
            "⚠️ توجه: لینک دانلود مستقیم از گوگل درایو ممکن است نیاز به احراز هویت داشته باشد.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"خطا در ارسال لینک: {e}")
        await handle_error(update, context)

async def show_contact(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی", callback_data='back_to_main')]]
    
    try:
        await query.edit_message_text(
            CONTACT_INFO,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطا در نمایش اطلاعات تماس: {e}")
        await handle_error(update, context)

async def button_click(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'contact':
            await show_contact(update, context)
        elif query.data.startswith('direct_'):
            _, course_type = query.data.split('_', 1)
            if course_type not in COURSES:
                raise ValueError(f"درس نامعتبر: {course_type}")
            await send_course_files(update, context, course_type)
        elif query.data.startswith('link_'):
            _, course_type = query.data.split('_', 1)
            if course_type not in COURSES:
                raise ValueError(f"درس نامعتبر: {course_type}")
            await send_drive_link(update, context, course_type)
        elif query.data in COURSES:
            await show_download_options(update, context, query.data)
        elif query.data == 'back_to_main':
            await start(update, context)
        else:
            await query.edit_message_text(text="🔄 محتوای این بخش به زودی اضافه میشود...")
            
    except Exception as e:
        logger.error(f"خطای کلی: {str(e)}")
        await handle_error(update, context)

async def handle_error(update: Update, context: CallbackContext):
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ خطایی رخ داد! لطفا دوباره امتحان کنید.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data='back_to_main')]
            ])
        )
    except Exception as e:
        logger.error(f"خطا در ارسال پیام خطا: {e}")

async def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception occurred:", exc_info=context.error)
    await handle_error(update, context)

def main():
    print("✅ The bot is now active!")

    
    
    for course in COURSES.values():
        os.makedirs(course['folder'], exist_ok=True)
        print(f"📂 The folder {course['folder']} has been created/verified")

    
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()