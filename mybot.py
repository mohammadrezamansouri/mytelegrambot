from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# /start command handler - Main menu
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Define main menu buttons with emojis
    keyboard = [
        [InlineKeyboardButton("💬 About Me", callback_data='about_me')],
        [InlineKeyboardButton("📂 My Projects", callback_data='my_projects')],
        [InlineKeyboardButton("📧 Contact Me", callback_data='contact_me')],
        [InlineKeyboardButton("🔗 LinkedIn", url='https://www.linkedin.com/')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Send a welcome message with the main menu
    if update.message:
        await update.message.reply_text(
            "Hello! Please select an option from the menu below:",
            reply_markup=reply_markup
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            "Hello! Please select an option from the menu below:",
            reply_markup=reply_markup
        )

# /my_projects handler
async def send_projects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Define project information with emojis
    projects_text = """
1. **Project 1**:
   Description of Project 1
   📥 Download: /dl1
   ----------------------------------
2. **Project 2**:
   Description of Project 2
   📥 Download: /dl2
   ----------------------------------
3. **Project 3**:
   Description of Project 3
   📥 Download: /dl3
   ----------------------------------
4. **Project 4**:
   Description of Project 4
   📥 Download: /dl4
   ----------------------------------
5. **Project 5**:
   Description of Project 5
   📥 Download: /dl5
   ----------------------------------
"""
    # Add a back button with an emoji
    back_button = [[InlineKeyboardButton("⬅ Back to Main Menu", callback_data='main_menu')]]
    reply_markup = InlineKeyboardMarkup(back_button)

    # Send project list with a back button
    await update.callback_query.edit_message_text(
        projects_text,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# Callback query handler for button clicks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    if query.data == "about_me":
        await query.edit_message_text(
            "I am a simple bot created by you. 😊",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Main Menu", callback_data='main_menu')]])
        )
    elif query.data == "my_projects":
        # Call the send_projects function to display project information
        await send_projects(update, context)
    elif query.data == "contact_me":
        await query.edit_message_text(
            "To contact me, please send a message or email me at: example@gmail.com",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅ Back to Main Menu", callback_data='main_menu')]])
        )
    elif query.data == "main_menu":
        # Redirect to the main menu
        await start(update, context)

# /dl command handlers for downloading projects
async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Determine the project being requested
    command = update.message.text
    if command == "/dl1":
        await update.message.reply_text("Download link for Project 1: [Click here](https://example.com/project1)", parse_mode="Markdown")
    elif command == "/dl2":
        await update.message.reply_text("Download link for Project 2: [Click here](https://example.com/project2)", parse_mode="Markdown")
    elif command == "/dl3":
        await update.message.reply_text("Download link for Project 3: [Click here](https://example.com/project3)", parse_mode="Markdown")
    elif command == "/dl4":
        await update.message.reply_text("Download link for Project 4: [Click here](https://example.com/project4)", parse_mode="Markdown")
    elif command == "/dl5":
        await update.message.reply_text("Download link for Project 5: [Click here](https://example.com/project5)", parse_mode="Markdown")
    else:
        await update.message.reply_text("Invalid download command. Please try again.")

if __name__ == '__main__':
    # Add your bot token here
    TOKEN = "7848642786:AAG4JQAhbGYrbZV2aNLO7Izq7vZwUEYbCvg"

    # Create the application
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers for commands and callbacks
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler(["dl1", "dl2", "dl3", "dl4", "dl5"], download_file))

    print("Bot is running...")
    # Start polling to handle updates
    app.run_polling()
