import os
import sys
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

from aiogram import Bot, Dispatcher, types, F

from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton

import database as db
import characters as chars
from llm_client import OpenRouterClient
from image_engine import generate_character_image

# Load tokens
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

if not BOT_TOKEN:
    print("Error: TELEGRAM_BOT_TOKEN is not set. Please specify it in .env or run setup.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
llm = OpenRouterClient(api_key=OPENROUTER_KEY)


# Keyboards
def get_chat_kb(character_id: str, affection: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📸 Попросить селфи / фото", callback_data=f"selfie:{character_id}"),
        InlineKeyboardButton(text="🔄 Сброс памяти", callback_data=f"reset:{character_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🎭 Сменить персонажа", callback_data="catalog"),
        InlineKeyboardButton(text="⚡ Профиль & Лимиты", callback_data="profile")
    )
    return builder.as_markup()

def get_catalog_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    # 18+ Hentai Section
    builder.row(InlineKeyboardButton(text="🔞 --- 18+ ХЕНТАЙ (100% СИМПАТИЯ) ---", callback_data="cat_header_3"))
    for c in chars.list_characters():
        if c.get("tier") == 3:
            builder.row(InlineKeyboardButton(text=c["name"], callback_data=f"select_char:{c['id']}"))

    # SFW Everyday Section
    builder.row(InlineKeyboardButton(text="💬 --- ДРУЗЬЯ & СОБЕСЕДНИКИ ---", callback_data="cat_header_1"))
    for c in chars.list_characters():
        if c.get("tier") == 1:
            builder.row(InlineKeyboardButton(text=c["name"], callback_data=f"select_char:{c['id']}"))

    builder.row(InlineKeyboardButton(text="⬅️ В чат", callback_data="back_to_chat"))
    return builder.as_markup()




def get_profile_kb() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎁 Ввести промокод", callback_data="enter_promo"),
        InlineKeyboardButton(text="🎭 Каталог", callback_data="catalog")
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в чат", callback_data="back_to_chat"))
    return builder.as_markup()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    char = chars.get_character(user["active_character_id"])
    affection = await db.get_affection(message.from_user.id, char["id"])

    welcome_text = (
        f"✨ <b>Добро пожаловать в Lucid AI!</b>\n\n"
        f"Здесь вы можете общаться с уникальными AI-персонажами, погружаться в интерактивные ролевые истории и получать живые фотографии прямо во время диалога.\n\n"
        f"🎭 <b>Текущий собеседник:</b> {char['name']}\n"
        f"📝 <i>{char['tagline']}</i>\n"
        f"💖 <b>Уровень привязанности:</b> {affection}/100\n\n"
        f"{char['greeting']}"
    )

    await message.answer(welcome_text, parse_mode="HTML", reply_markup=get_chat_kb(char["id"], affection))

@dp.message(Command("catalog"))
async def cmd_catalog(message: types.Message):
    await message.answer("🎭 <b>Выберите персонажа для общения:</b>", parse_mode="HTML", reply_markup=get_catalog_kb())

@dp.message(Command("profile"))
async def cmd_profile(message: types.Message):
    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    char = chars.get_character(user["active_character_id"])
    affection = await db.get_affection(message.from_user.id, char["id"])

    status_str = "💎 <b>UNLIMITED (Безлимит активен)</b>" if user["is_unlimited"] else "⚡ <b>Стандартный аккаунт</b>"
    
    if user["is_unlimited"]:
        until_dt = datetime.fromtimestamp(user["unlimited_until"]).strftime("%d.%m.%Y %H:%M")
        status_str += f"\n⏳ Действует до: {until_dt}"

    text = (
        f"👤 <b>Ваш профиль:</b>\n\n"
        f"Статус: {status_str}\n"
        f"💬 Сообщения: <b>{user['energy'] if not user['is_unlimited'] else '∞'}</b> / 25 в день\n"
        f"📸 Генерация фото: <b>{user['photo_energy'] if not user['is_unlimited'] else '∞'}</b> / 5 в день\n\n"
        f"🎭 <b>Активный персонаж:</b> {char['name']}\n"
        f"💖 <b>Симпатия:</b> {affection}/100\n"
    )

    await message.answer(text, parse_mode="HTML", reply_markup=get_profile_kb())

@dp.message(Command("promo"))
async def cmd_promo(message: types.Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: <code>/promo ВАШ_ПРОМОКОД</code>", parse_mode="HTML")
        return

    code = args[1].strip()
    ok, msg = await db.activate_promo(message.from_user.id, code)
    if ok:
        await message.answer(f"🎉 <b>Успешно!</b>\n\n{msg}", parse_mode="HTML")
    else:
        await message.answer(f"❌ {msg}")

@dp.callback_query(F.data.startswith("cat_header_"))
async def callback_cat_header(callback: types.CallbackQuery):
    await callback.answer()

@dp.callback_query(F.data.startswith("select_char:"))

async def callback_select_char(callback: types.CallbackQuery):
    char_id = callback.data.split(":")[1]
    char = chars.get_character(char_id)
    await db.set_active_character(callback.from_user.id, char_id)
    await db.clear_history(callback.from_user.id, char_id)
    affection = await db.get_affection(callback.from_user.id, char_id)

    text = (
        f"🎭 <b>Вы переключились на: {char['name']}</b>\n"
        f"<i>{char['tagline']}</i>\n\n"
        f"{char['greeting']}"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_chat_kb(char_id, affection))
    await callback.answer(f"Выбран: {char['name']}")

@dp.callback_query(F.data == "catalog")
async def callback_catalog(callback: types.CallbackQuery):
    await callback.message.edit_text("🎭 <b>Выберите персонажа для общения:</b>", parse_mode="HTML", reply_markup=get_catalog_kb())
    await callback.answer()

@dp.callback_query(F.data == "profile")
async def callback_profile(callback: types.CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    char = chars.get_character(user["active_character_id"])
    affection = await db.get_affection(callback.from_user.id, char["id"])

    status_str = "💎 <b>UNLIMITED (Безлимит)</b>" if user["is_unlimited"] else "⚡ <b>Стандартный</b>"
    if user["is_unlimited"]:
        until_dt = datetime.fromtimestamp(user["unlimited_until"]).strftime("%d.%m.%Y %H:%M")
        status_str += f"\n⏳ До: {until_dt}"

    text = (
        f"👤 <b>Ваш профиль:</b>\n\n"
        f"Статус: {status_str}\n"
        f"💬 Сообщения: <b>{user['energy'] if not user['is_unlimited'] else '∞'}</b> / 25\n"
        f"📸 Фото: <b>{user['photo_energy'] if not user['is_unlimited'] else '∞'}</b> / 5\n\n"
        f"🎭 <b>Собеседник:</b> {char['name']}\n"
        f"💖 <b>Симпатия:</b> {affection}/100"
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_profile_kb())
    await callback.answer()

@dp.callback_query(F.data == "back_to_chat")
async def callback_back(callback: types.CallbackQuery):
    user = await db.get_or_create_user(callback.from_user.id, callback.from_user.username)
    char = chars.get_character(user["active_character_id"])
    affection = await db.get_affection(callback.from_user.id, char["id"])

    await callback.message.edit_text(
        f"💬 Чат с <b>{char['name']}</b> возобновлен.\n\nПродолжайте диалог, просто отправив сообщение!",
        parse_mode="HTML",
        reply_markup=get_chat_kb(char["id"], affection)
    )
    await callback.answer()

@dp.callback_query(F.data == "enter_promo")
async def callback_enter_promo(callback: types.CallbackQuery):
    await callback.message.answer("🎁 Чтобы активировать промокод, отправьте в чат:\n<code>/promo ВАШ_ПРОМОКОД</code>", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("reset:"))
async def callback_reset(callback: types.CallbackQuery):
    char_id = callback.data.split(":")[1]
    char = chars.get_character(char_id)
    await db.clear_history(callback.from_user.id, char_id)
    affection = await db.get_affection(callback.from_user.id, char_id)

    await callback.message.edit_text(
        f"🔄 <b>Память диалога сброшена!</b>\n\n{char['greeting']}",
        parse_mode="HTML",
        reply_markup=get_chat_kb(char_id, affection)
    )
    await callback.answer("Диалог начат сначала!")

@dp.callback_query(F.data.startswith("selfie:"))
async def callback_selfie(callback: types.CallbackQuery):
    char_id = callback.data.split(":")[1]
    char = chars.get_character(char_id)

    can_photo = await db.deduct_energy(callback.from_user.id, is_photo=True)
    if not can_photo:
        await callback.answer("❌ Лимит генераций фото на сегодня исчерпан!", show_alert=True)
        return

    await callback.answer("📸 Персонаж делает фото...")
    status_msg = await callback.message.answer(f"📸 <i>{char['name']} делает фото для вас...</i>", parse_mode="HTML")

    # Get recent context for dynamic clothing/scene prompt
    history = await db.get_history(callback.from_user.id, char_id, limit=6)
    context_str = " ".join([f"{h['role']}: {h['content']}" for h in history]) if history else "standing casually, looking at camera"

    # Convert to Danbooru tags via LLM
    photo_prompt = await llm.generate_photo_prompt(char["prompt_tags"], context_str)
    logging.info(f"Generated Photo Prompt for {char_id}: {photo_prompt}")
    
    # Generate on local Forge
    img_bytes, err = await generate_character_image(photo_prompt)

    await status_msg.delete()

    if img_bytes:
        affection = await db.add_affection(callback.from_user.id, char_id, amount=3)
        caption = f"✨ <i>{char['name']} прислала вам фото!</i>\n💖 Симпатия: {affection}/100"
        photo_file = BufferedInputFile(img_bytes, filename="selfie.png")
        await callback.message.answer_photo(photo_file, caption=caption, parse_mode="HTML", reply_markup=get_chat_kb(char_id, affection))
    else:
        await callback.message.answer(f"⚠️ Не удалось сгенерировать фото: {err}\n<i>(Убедитесь, что Stable Diffusion Forge запущен на 127.0.0.1:7860)</i>", parse_mode="HTML")

# Message Handler (Roleplay Chat)
@dp.message()
async def handle_chat_message(message: types.Message):
    if not message.text or message.text.startswith("/"):
        return

    # Check energy limit
    can_send = await db.deduct_energy(message.from_user.id, is_photo=False)
    if not can_send:
        await message.answer(
            "⚡ <b>Лимит сообщений на сегодня исчерпан!</b>\n\n"
            "Энергия восстанавливается каждые 24 часа. Используйте <code>/promo</code> для активации бонуса.",
            parse_mode="HTML"
        )
        return

    user = await db.get_or_create_user(message.from_user.id, message.from_user.username)
    char_id = user["active_character_id"]
    char = chars.get_character(char_id)

    # Save user message
    await db.save_message(message.from_user.id, char_id, "user", message.text)
    
    # Typing indicator
    await bot.send_chat_action(message.chat.id, "typing")

    # Load history
    history = await db.get_history(message.from_user.id, char_id, limit=10)

    # Dynamic affection context
    is_t3 = char.get("tier") == 3
    affection = await db.get_affection(message.from_user.id, char_id, default_base=char.get("base_affection", 10))
    dynamic_system_prompt = f"{char['system_prompt']}\n[Current Affection with User: {affection}/100]"

    # Generate response
    main_text, suggestions = await llm.generate_reply(
        system_prompt=dynamic_system_prompt,
        history=history[:-1],  # exclude current to avoid duplicate
        user_message=message.text,
        is_tier3=is_t3
    )

    # Save assistant reply
    await db.save_message(message.from_user.id, char_id, "assistant", main_text)
    new_affection = await db.add_affection(message.from_user.id, char_id, amount=1)

    # Format response with Tier 3 choices
    if is_t3 and suggestions:
        choices_str = "\n".join([f"<b>{i}.</b> {s}" for i, s in enumerate(suggestions, 1)])
        final_msg = (
            f"{main_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 <b>Варианты действий:</b>\n"
            f"{choices_str}\n\n"
            f"✏️ <i>(Отправьте номер варианта 1-3 или напишите свой собственный текст)</i>"
        )
        await message.answer(final_msg, parse_mode="HTML", reply_markup=get_chat_kb(char_id, new_affection))
    else:
        await message.answer(main_text, reply_markup=get_chat_kb(char_id, new_affection))




async def main():
    await db.init_db()
    print("=== [LucidBot AI Platform Started] ===")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
