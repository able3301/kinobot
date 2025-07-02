import logging
import json
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

# ========== CONFIGURATION ==========
TOKEN = "8046803096:AAH625U_9kRIErhsgZ8Dl7-qOoaXFAzb2CQ"  # Bu yerga o'z tokeningizni yozing
MAIN_ADMIN_ID = 857016431

ADMINS_FILE = "admins.json"
USERS_FILE = "users.json"
CODES_FILE = "codes.json"
USAGE_FILE = "usage.json"
CHANNELS_FILE = "channels.json"
ANNOUNCEMENTS_FILE = "announcements.json"
def save_channels():
    save_json(CHANNELS_FILE, CHANNELS)

def save_announcements():
    save_json(ANNOUNCEMENTS_FILE, ANNOUNCEMENTS)

# ========== LOGGER ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== FILE STORAGE ==========
def load_json(file, default):
    if os.path.exists(file):
        try:
            with open(file, 'r') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=2)

ADMINS = load_json(ADMINS_FILE, [MAIN_ADMIN_ID])
USERS = load_json(USERS_FILE, [])
CODES = load_json(CODES_FILE, {})
USAGE = load_json(USAGE_FILE, {})
CHANNELS = load_json(CHANNELS_FILE, ["@KINOSPEEDS", "@informatiklaruzbN1"])
ANNOUNCEMENTS = load_json(ANNOUNCEMENTS_FILE, [])

# ========== UTILS ==========
def is_admin(user_id):
    return user_id in ADMINS

def register_user(user_id):
    if user_id not in USERS:
        USERS.append(user_id)
        save_json(USERS_FILE, USERS)

def count_usage(code):
    USAGE[code] = USAGE.get(code, 0) + 1
    save_json(USAGE_FILE, USAGE)

def build_subscription_keyboard():
    buttons = [
        [InlineKeyboardButton(f"{i+1}. Kanalga o'tish", url=f"https://t.me/{c.lstrip('@')}")]
        for i, c in enumerate(CHANNELS)
    ]
    buttons.append([
        InlineKeyboardButton("✅ A'zolikni tekshirish", callback_data="check_membership")
    ])
    return InlineKeyboardMarkup(buttons)

def build_admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin"),
            InlineKeyboardButton("➖ Admin o'chirish", callback_data="remove_admin")
        ],
        [
            InlineKeyboardButton("👥 Adminlar ro'yxati", callback_data="list_admins")
        ],
        [
            InlineKeyboardButton("➕ Kanal qo'shish", callback_data="add_channel"),
            InlineKeyboardButton("➖ Kanal o'chirish", callback_data="remove_channel")
        ],
        [
            InlineKeyboardButton("📋 Kanallar ro'yxati", callback_data="list_channels")
        ],
        [
            InlineKeyboardButton("📝 E'lon qo'shish", callback_data="add_announcement"),
            InlineKeyboardButton("🗑 E'lon o'chirish", callback_data="remove_announcement")
        ],
        [
            InlineKeyboardButton("📋 E'lonlar ro'yxati", callback_data="list_announcements"),
            InlineKeyboardButton("📢 E'lon yuborish", callback_data="send_announcement")
        ],
        [
            InlineKeyboardButton("📦 Kodlar ro'yxati", callback_data="list_codes")
        ],
        [
            InlineKeyboardButton("🗑 Kodni o'chirish", callback_data="delete_code")
        ],
        [
            InlineKeyboardButton("📹 Yuklangan videolarni ko'rish", callback_data="view_videos")
        ],
        [
            InlineKeyboardButton("📈 Statistika", callback_data="stats")
        ]
    ])

def build_videos_keyboard(code):
    videos = CODES.get(code, {}).get("videos", [])
    keyboard = [
        [InlineKeyboardButton(f"{i+1}-qism", callback_data=f"play_{code}_{i}")]
        for i in range(len(videos))
    ]
    return InlineKeyboardMarkup(keyboard)



async def check_membership(user_id, context):
    for ch in CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            logger.error(f"check_membership error: {e}")
            return False
    return True
# ========== STATES ==========
WAITING_FOR_VIDEOS, WAITING_FOR_CAPTIONS, WAITING_FOR_CODE = range(3)

# ========== START COMMAND ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id)

    # E'lonlar mavjud bo'lsa, ularni chiqarish
    if ANNOUNCEMENTS:
        text = "📢 E'lonlar:\n\n" + "\n\n".join(f"• {a}" for a in ANNOUNCEMENTS)
        await update.message.reply_text(text)

    await update.message.reply_text(
        "👋 Assalomu alaykum!\n\nQuyidagi kanallarga a'zo bo'ling:",
        reply_markup=build_subscription_keyboard()
    )

async def check_membership_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if await check_membership(user_id, context):
        await query.edit_message_text(
            "✅ Obuna tasdiqlandi! Endi kod yuboring."
        )
    else:
        await query.edit_message_text(
            "❌ Siz hali barcha kanallarga a'zo emassiz!\nQuyidagi kanallarga a'zo bo'ling:",
            reply_markup=build_subscription_keyboard()
        )

# ========== USER PANEL ==========
async def user_send_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    register_user(user_id)

    if not await check_membership(user_id, context):
        await update.message.reply_text(
            "❌ Siz hali barcha kanallarga a'zo emassiz!\nQuyidagi kanallarga a'zo bo'ling:",
            reply_markup=build_subscription_keyboard()
        )
        return

    code = update.message.text.strip()
    if code in CODES:
        count_usage(code)
        code_data = CODES[code]
        if "videos" in code_data:
            await update.message.reply_text(
                "🎬 Bu kod ostidagi videolar ro'yxati:\nTanlang:",
                reply_markup=build_videos_keyboard(code)
            )
        else:
            await update.message.reply_video(
                code_data["file_id"],
                caption=f"✅ {code_data['caption']}"
            )
    else:
        await update.message.reply_text("❌ Noto'g'ri kod. Iltimos, to'g'ri kod yuboring.")

async def user_video_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if "_" not in data:
        await query.edit_message_text("❌ Kodni qayta yuboring.")
        return

    code, idx = data.split("_")[1:]
    idx = int(idx)
    if code in CODES and "videos" in CODES[code]:
        video_info = CODES[code]["videos"][idx]
        await context.bot.send_video(
            chat_id=query.from_user.id,
            video=video_info["file_id"],
            caption=f"✅ {video_info['caption']}"
        )
        await query.message.reply_text(
            "🎬 Qaytadan tanlash uchun:",
            reply_markup=build_videos_keyboard(code)
        )
    else:
        await query.edit_message_text("❌ Topilmadi. Kod noto'g'ri yoki o'chirilgan.")
# ========== ADMIN PANEL ==========
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return

    await update.message.reply_text(
        "✅ Admin paneli:",
        reply_markup=build_admin_panel_keyboard()
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if user_id not in ADMINS:
        await query.edit_message_text("❌ Siz admin emassiz!")
        return

    data = query.data

    if data == "add_admin":
        context.user_data["awaiting_add_admin"] = True
        await query.edit_message_text("🆕 Qo'shmoqchi bo'lgan admin ID raqamini yuboring:")
    elif data == "remove_admin":
        context.user_data["awaiting_remove_admin"] = True
        await query.edit_message_text("🗑 O'chiriladigan admin ID raqamini yuboring:")
    elif data == "list_admins":
        text = "👥 Adminlar ro'yxati:\n" + "\n".join([str(a) for a in ADMINS])
        await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())
    elif data == "list_codes":
        text = "📦 Kodlar:\n" + "\n".join([f"{k}" for k in CODES]) if CODES else "❗️ Kodlar yo'q"
        await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())
    elif data == "delete_code":
        context.user_data["awaiting_delete_code"] = True
        await query.edit_message_text("🗑 O'chiriladigan kodni yuboring:")
    elif data == "view_videos":
        lines = []
        for k, v in CODES.items():
            if "videos" in v:
                lines.append(f"✅ Kod {k}: {len(v['videos'])} ta video")
            else:
                lines.append(f"✅ Kod {k}: 1 ta video")
        text = "\n".join(lines) or "❗️ Hali hech narsa yo'q."
        await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())
    elif data == "stats":
        total_codes = len(CODES)
        total_users = len(USERS)
        text = f"📈 Kodlar soni: {total_codes}\n👥 Foydalanuvchilar: {total_users}\n"
        text += "\nKodlar bo'yicha foydalanishlar:\n"
        for code, count in USAGE.items():
            text += f"✅ {code}: {count} ta marta\n"
        await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())
    elif data == "add_channel":
        context.user_data["awaiting_add_channel"] = True
        await query.edit_message_text("🆕 Yangi kanalni username sifatida yuboring (masalan: @kanalusername):")
    elif data == "remove_channel":
        context.user_data["awaiting_remove_channel"] = True
        await query.edit_message_text("🗑 O'chiriladigan kanal username sini yuboring (masalan: @kanalusername):")
    elif data == "list_channels":
        if CHANNELS:
            text = "📜 Kanallar ro'yxati:\n" + "\n".join(CHANNELS)
        else:
            text = "❗️ Kanallar ro'yxati bo'sh."
        await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())
    elif data == "send_announcement":
        context.user_data["awaiting_announcement"] = True
        await query.edit_message_text("📢 Yuboriladigan e’lon matnini yozing:")

    
    
    elif data == "add_announcement":
        context.user_data["awaiting_add_announcement"] = True
        await query.edit_message_text("📝 Yangi e’lon matnini yozing:")

    elif data == "remove_announcement":
        context.user_data["awaiting_remove_announcement"] = True
        await query.edit_message_text("🗑 O'chiriladigan e’lon matnini to‘liq yozing:")

    elif data == "list_announcements":
        if ANNOUNCEMENTS:
            text = "📋 E’lonlar ro’yxati:\n" + "\n".join(f"• {a}" for a in ANNOUNCEMENTS)
    else:
        text = "❗️ Hali e’lonlar yo‘q."
    await query.edit_message_text(text, reply_markup=build_admin_panel_keyboard())


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if user_id not in ADMINS:
        return

    if context.user_data.get("awaiting_add_admin"):
        try:
            new_id = int(text)
            if new_id not in ADMINS:
                ADMINS.append(new_id)
                save_json(ADMINS_FILE, ADMINS)
                await update.message.reply_text("✅ Admin qo'shildi!")
            else:
                await update.message.reply_text("⚠️ Bu ID allaqachon admin.")
        except ValueError:
            await update.message.reply_text("❗️ Raqam kiriting.")
        context.user_data.pop("awaiting_add_admin")
    elif context.user_data.get("awaiting_remove_admin"):
        try:
            rem_id = int(text)
            if rem_id in ADMINS:
                ADMINS.remove(rem_id)
                save_json(ADMINS_FILE, ADMINS)
                await update.message.reply_text("✅ Admin o'chirildi!")
            else:
                await update.message.reply_text("❗️ Topilmadi.")
        except ValueError:
            await update.message.reply_text("❗️ Raqam kiriting.")
        context.user_data.pop("awaiting_remove_admin")
    elif context.user_data.get("awaiting_delete_code"):
        if text in CODES:
            del CODES[text]
            save_json(CODES_FILE, CODES)
            await update.message.reply_text("✅ Kod o'chirildi!")
        else:
            await update.message.reply_text("❗️ Kod topilmadi.")
        context.user_data.pop("awaiting_delete_code")
    elif context.user_data.get("awaiting_add_channel"):
        ch = text.strip()
        if ch.startswith("@") and ch not in CHANNELS:
            CHANNELS.append(ch)
            await update.message.reply_text(f"✅ Kanal qo'shildi: {ch}")
        else:
            await update.message.reply_text("❗️ Noto'g'ri yoki mavjud kanal.")
        context.user_data.pop("awaiting_add_channel")
    elif context.user_data.get("awaiting_remove_channel"):
        ch = text.strip()
        if ch in CHANNELS:
            CHANNELS.remove(ch)
            await update.message.reply_text(f"✅ Kanal o'chirildi: {ch}")
        else:
            await update.message.reply_text("❗️ Kanal topilmadi.")
        context.user_data.pop("awaiting_remove_channel")
   
    elif context.user_data.get("awaiting_announcement"):
        announcement = text.strip()
    if announcement and announcement not in ANNOUNCEMENTS:
        ANNOUNCEMENTS.append(announcement)
        save_announcements()
        await update.message.reply_text("✅ E’lon qo'shildi!")
    else:
        await update.message.reply_text("❗️ Noto'g'ri yoki mavjud e’lon.")
    context.user_data.pop("awaiting_announcement")

    if context.user_data.get("awaiting_announcement_broadcast"):
        announcement = text.strip()
    else:
        await user_send_code(update, context)

    for uid in USERS:
        try:
            await context.bot.send_message(uid, f"📢 E’lon:\n\n{announcement}")
        except Exception as e:
            logger.warning(f"E’lon yuborishda xato: {e}")
    await update.message.reply_text("✅ E’lon barcha foydalanuvchilarga yuborildi!")
    context.user_data.pop("awaiting_announcement_broadcast")
 

   
   
   
    
    
# ========== ADMIN UPLOAD CONVERSATION ==========
WAITING_FOR_VIDEOS, WAITING_FOR_CAPTIONS, WAITING_FOR_CODE = range(3)

async def admin_start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id not in ADMINS:
        await update.message.reply_text("❌ Siz admin emassiz!")
        return ConversationHandler.END

    context.user_data["videos"] = []
    context.user_data["captions"] = []
    await update.message.reply_text(
        "📥 Videolarni yuboring. Tugatgach '✅ TAMOM' deb yozing."
    )
    return WAITING_FOR_VIDEOS

async def receive_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("video"):
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text("❌ Video fayl yuboring!")
        return WAITING_FOR_VIDEOS

    context.user_data["videos"].append(file_id)
    await update.message.reply_text(f"✅ Video qabul qilindi. Davom eting yoki '✅ TAMOM' deb yozing.")
    return WAITING_FOR_VIDEOS

async def finish_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("videos"):
        await update.message.reply_text("❗️ Hech qanday video qabul qilinmadi. Boshlash uchun /upload.")
        return ConversationHandler.END

    context.user_data["captions"] = []
    context.user_data["caption_index"] = 0
    await update.message.reply_text(
        "✏️ Endi har bir videoga izoh yozing.\nHar bir izohdan keyin yuboring."
    )
    await update.message.reply_text(f"1️⃣ - video uchun izoh:")
    return WAITING_FOR_CAPTIONS

async def receive_captions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    context.user_data["captions"].append(text)
    context.user_data["caption_index"] += 1

    if context.user_data["caption_index"] < len(context.user_data["videos"]):
        await update.message.reply_text(
            f"{context.user_data['caption_index'] + 1}️⃣ - video uchun izoh:"
        )
        return WAITING_FOR_CAPTIONS

    await update.message.reply_text(
        "✅ Izohlar qabul qilindi.\n📌 Endi kodni kiriting (masalan: 123 yoki SERIAL2024):"
    )
    return WAITING_FOR_CODE

async def receive_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    if len(code) < 3:
        await update.message.reply_text("❗️ Kod kamida 3 ta belgidan iborat bo'lishi kerak.")
        return WAITING_FOR_CODE

    if code in CODES:
        await update.message.reply_text("⚠️ Bu kod allaqachon mavjud. Iltimos, yangi kod kiriting.")
        return WAITING_FOR_CODE

    videos_list = [
        {"file_id": context.user_data["videos"][i], "caption": context.user_data["captions"][i]}
        for i in range(len(context.user_data["videos"]))
    ]
    CODES[code] = {"videos": videos_list}
    save_json(CODES_FILE, CODES)

    await update.message.reply_text(
        f"✅ Videolar saqlandi!\nKod: {code}",
        reply_markup=ReplyKeyboardRemove()
    )
    context.user_data.clear()
    return ConversationHandler.END
# ========== MAIN ==========

def main():
    app = Application.builder().token(TOKEN).build()

    # ✅ ConversationHandler faqat ADMINlar uchun — /upload
    upload_handler = ConversationHandler(
        entry_points=[
            CommandHandler("upload", admin_start_upload, filters.ChatType.PRIVATE & filters.User(ADMINS))
        ],
        states={
            WAITING_FOR_VIDEOS: [
                MessageHandler(
                    (filters.VIDEO | filters.Document.VIDEO) & filters.ChatType.PRIVATE & filters.User(ADMINS),
                    receive_videos
                ),
                MessageHandler(
                    filters.TEXT & filters.Regex("^(✅|tamom|TAMOM|Tamom)$") & filters.ChatType.PRIVATE & filters.User(ADMINS),
                    finish_videos
                )
            ],
            WAITING_FOR_CAPTIONS: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMINS), receive_captions)
            ],
            WAITING_FOR_CODE: [
                MessageHandler(filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMINS), receive_code)
            ],
        },
        fallbacks=[],
        allow_reentry=True
    )
    app.add_handler(upload_handler)

    # ✅ /admin — faqat adminlar uchun
    app.add_handler(CommandHandler("admin", admin_command, filters.ChatType.PRIVATE & filters.User(ADMINS)))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^(add_|remove_|list_|delete_|view_|stats)"))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & filters.User(ADMINS),
        admin_text_handler
    ))

    # ✅ Oddiy foydalanuvchilar uchun — /start va kod kiritish
    app.add_handler(CommandHandler("start", start, filters.ChatType.PRIVATE))
    app.add_handler(CallbackQueryHandler(check_membership_button, pattern="^check_membership$"))
    app.add_handler(CallbackQueryHandler(user_video_button_handler, pattern=r"^play_\w+_\d+$"))
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE,
        user_send_code
    ))

    logger.info("✅ Bot ishga tushdi!")
    app.run_polling()


if __name__ == '__main__':
    main()

