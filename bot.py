import logging
import sys
from datetime import datetime, timezone, timedelta, timezone, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ============================================================
# SETTINGS
# ============================================================
BOT_TOKEN = "8510694816:AAEr7knDk106LBRXYCTLBMD2unRh2D5WjAo"
ADMIN_IDS = [7399101034]
GROUP_CHAT_ID = -1004313070352
# ============================================================

# Clean logging — only show critical errors
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.CRITICAL,
    stream=sys.stdout
)

# Silence noisy libraries
for lib in ("httpx", "httpcore", "telegram", "apscheduler"):
    logging.getLogger(lib).setLevel(logging.CRITICAL)

logger = logging.getLogger(__name__)

CHOOSE_TYPE, GET_USERNAME, GET_ID, GET_ASSET, GET_AMOUNT, CONFIRM = range(6)

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

def format_receipt(data: dict) -> str:
    TASHKENT = timezone(timedelta(hours=5))
    now = datetime.now(TASHKENT).strftime("%d.%m.%Y %H:%M")
    username = data["username"].lstrip("@")
    asset = data["asset"].upper()
    lines = (
        f"TYPE: {data['type']}\n\n"
        f"USERNAME: @{username}\n"
        f"ID: {data['id_code']}\n\n"
        f"ASSET: {asset}\n"
        f"AMOUNT: {data['amount']} {asset}\n\n"
        f"STATUS: COMPLETED\n"
        f"DATE: {now}"
    )
    return f"```\n{lines}\n```"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data.clear()
    keyboard = [[
        InlineKeyboardButton("BUY", callback_data="type_BUY"),
        InlineKeyboardButton("SELL", callback_data="type_SELL")
    ]]
    await update.message.reply_text(
        "Select type:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSE_TYPE

async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["type"] = query.data.replace("type_", "")
    await query.edit_message_text("USERNAME:")
    return GET_USERNAME

async def get_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data["username"] = update.message.text.strip()
    await update.message.reply_text("ID:")
    return GET_ID

async def get_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data["id_code"] = update.message.text.strip()
    await update.message.reply_text("ASSET:")
    return GET_ASSET

async def get_asset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data["asset"] = update.message.text.strip().upper()
    await update.message.reply_text("AMOUNT:")
    return GET_AMOUNT

async def get_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    context.user_data["amount"] = update.message.text.strip()
    receipt = format_receipt(context.user_data)
    keyboard = [[
        InlineKeyboardButton("Send", callback_data="confirm_yes"),
        InlineKeyboardButton("Cancel", callback_data="cancel")
    ]]
    await update.message.reply_text(
        f"Preview:\n\n{receipt}\n\nSend to group?",
        parse_mode="MarkdownV2",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def confirm_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    receipt = format_receipt(context.user_data)
    try:
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=receipt,
            parse_mode="MarkdownV2"
        )
        await query.edit_message_text("Sent.")
    except Exception as e:
        await query.edit_message_text(f"Error: {e}")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Cancelled. Use /start to begin again.")
    else:
        await update.message.reply_text("Cancelled. Use /start to begin again.")
    context.user_data.clear()
    return ConversationHandler.END

async def unknown_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .connect_timeout(30)
        .read_timeout(30)
        .write_timeout(30)
        .build()
    )

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_TYPE:  [CallbackQueryHandler(choose_type, pattern="^type_")],
            GET_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_username)],
            GET_ID:       [MessageHandler(filters.TEXT & ~filters.COMMAND, get_id)],
            GET_ASSET:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_asset)],
            GET_AMOUNT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_amount)],
            CONFIRM: [
                CallbackQueryHandler(confirm_send, pattern="^confirm_yes$"),
                CallbackQueryHandler(cancel, pattern="^cancel$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("start", start),
        ],
    )

    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.ALL, unknown_user))

    print("Bot is running...")
    app.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES
    )

if __name__ == "__main__":
    main()
