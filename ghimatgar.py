import os
import logging
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

#API
GOOGLE_API_KEY = 'AIzaSyC53b7n-px8gnM7-govA1LMDMY0Qr7Qzr4'
TOKEN = "7434501070:AAFuuTwyLg0T4oENbAvMgspW3YEyMlgYSjg"


SMART_CHAT, END_CHAT = range(2)


COURSES = {
    'dsp': {
        'folder': 'dsp',
        'name': 'درس پردازش سیگنال دیجیتال',
        'drive_link': 'https://drive.google.com/drive/folders/1qtsdaBt-tmNruB45o7pKHSKIMxyZS2mC?usp=sharing'
    },
    'adv_dsp': {
        'folder': 'adsp',
        'name': 'درس پردازش سیگنال های دیجیتال پیشرفته',
        'drive_link': 'https://drive.google.com/drive/folders/1YpsQwMb-Seju7Q3cgkI9QTDrxiOmdiGQ?usp=sharing'
    },
    'comm_circuit': {
        'folder': 'medar',
        'name': 'درس مدار مخابراتی',
        'drive_link': 'YOUR_GOOGLE_DRIVE_LINK_HERE'
    }
}

# call
CONTACT_INFO = """
📞 اطلاعات تماس:

➖➖➖➖➖➖

📱 تلفن: 
09394959842

📧 ایمیل: 
ghimatgar@pgu.ac.ir

تلگرام:
@Hgh9816

➖➖➖➖➖➖
"""

# logg
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

#Gemini
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro')

class GoogleAIChat:
    @staticmethod
    async def generate_response(prompt: str) -> str:
        """ارسال درخواست به Gemini API"""
        try:
            response = model.generate_content(
                f"شما یک دستیار آموزشی فارسی هستید. به سوالات مرتبط با آموزش پاسخ دهید. سوال: {prompt}",
                safety_settings={
                    'HARM_CATEGORY_HARASSMENT': 'block_none',
                    'HARM_CATEGORY_HATE_SPEECH': 'block_none',
                    'HARM_CATEGORY_SEXUALLY_EXPLICIT': 'block_none',
                    'HARM_CATEGORY_DANGEROUS_CONTENT': 'block_none'
                },
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=1000,
                    temperature=0.7
                )
            )
            return response.text
            
        except Exception as e:
            logger.error(f"خطای Gemini API: {str(e)}")
            return "⚠️ خطا در پردازش سوال. لطفا مجددا تلاش کنید"

async def start(update: Update, context: CallbackContext):
    try:
        keyboard = [
            [InlineKeyboardButton("📡 " + COURSES['dsp']['name'], callback_data='dsp')],
            [InlineKeyboardButton("🎛 " + COURSES['adv_dsp']['name'], callback_data='adv_dsp')],
            [InlineKeyboardButton("📶 " + COURSES['comm_circuit']['name'], callback_data='comm_circuit')],
            [InlineKeyboardButton("💬 چت هوشمند", callback_data='smart_chat')],
            [InlineKeyboardButton("📞 ارتباط با من", callback_data='contact')]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                '👨🏫 به ربات آموزشی دکتر قیمتگر خوش آمدید!\n'
                'لطفاً گزینه مورد نظر را انتخاب کنید:',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                '👨🏫 به ربات آموزشی دکتر قیمتگر خوش آمدید!\n'
                'لطفاً گزینه مورد نظر را انتخاب کنید:',
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
            InlineKeyboardButton("📥 دریافت مستقیم", callback_data=f"direct_{course_type}"),
            InlineKeyboardButton("🌐 گوگل درایو", callback_data=f"link_{course_type}")
        ],
        [InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]
    ]
    
    try:
        await query.edit_message_text(
            f"📚 {course['name']}\n"
            "روش دریافت را انتخاب کنید:",
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
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    
    try:
        await query.edit_message_text(
            f"🔗 لینک گوگل درایو {course['name']}:\n"
            f"{course['drive_link']}\n\n"
            "⚠️ توجه: ممکن است نیاز به احراز هویت داشته باشد.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=True
        )
    except Exception as e:
        logger.error(f"خطا در ارسال لینک: {e}")
        await handle_error(update, context)

async def show_contact(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data='back_to_main')]]
    
    try:
        await query.edit_message_text(
            CONTACT_INFO,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    except Exception as e:
        logger.error(f"خطا در نمایش اطلاعات تماس: {e}")
        await handle_error(update, context)

async def start_smart_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    
    keyboard = [[InlineKeyboardButton("🔙 پایان چت", callback_data='end_chat')]]
    
    await query.edit_message_text(
        "💬 حالت چت هوشمند فعال شد!\n"
        "سوالات آموزشی خود را مطرح کنید:\n\n"
        "⚠️ توجه: این سیستم از هوش مصنوعی Gemini گوگل استفاده می‌کند",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return SMART_CHAT

async def handle_chat_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        response = await GoogleAIChat.generate_response(user_message)
        
        await update.message.reply_text(
            f"🤖 پاسخ هوشمند:\n\n{response}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پایان چت", callback_data='end_chat')]])
        )
        
    except Exception as e:
        logger.error(f"خطا در پردازش پیام: {e}")
        await update.message.reply_text("⚠️ خطایی در پردازش سوال رخ داد!")
    
    return SMART_CHAT

async def end_chat(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    await start(update, context)
    return ConversationHandler.END

async def button_click(update: Update, context: CallbackContext):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'contact':
            await show_contact(update, context)
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
        else:
            await query.edit_message_text(text="🔄 این بخش به زودی اضافه خواهد شد")
            
    except Exception as e:
        logger.error(f"خطای کلی: {str(e)}")
        await handle_error(update, context)

async def handle_error(update: Update, context: CallbackContext):
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="⚠️ خطایی رخ داد! لطفا دوباره تلاش کنید",
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
    
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_smart_chat, pattern='^smart_chat$')],
        states={
            SMART_CHAT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_chat_message),
                CallbackQueryHandler(end_chat, pattern='^end_chat$')
            ],
        },
        fallbacks=[CommandHandler('start', start)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_error_handler(error_handler)
    
    application.run_polling()

if __name__ == '__main__':
    main()