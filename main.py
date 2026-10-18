import asyncio
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, CallbackQuery,
    InlineKeyboardButton, InlineKeyboardMarkup
)
from aiogram.enums import ParseMode

# ==================== НАСТРОЙКИ ====================
BOT_TOKEN = "ВСТАВЬТЕ_СЮДА_ТОКЕН_ОТ_BOTFATHER"
ADMIN_ID = 7759191824  # Ваш ID для получения обращений

# Словарь для хранения связи: ID сообщения админа -> ID пользователя
ticket_map = {}
# ===================================================

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и роутера
bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# Состояния FSM (для пошагового ввода)
class SupportStates(StatesGroup):
    waiting_for_message = State()

# ==================== КЛАВИАТУРЫ ====================
def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💜 Написать в поддержку", callback_data="create_ticket")]
    ])
    return kb

# ==================== ХЕНДЛЕРЫ ====================

# 1. Команда /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    text = (
        f"━━━━━━ 💜 ━━━━━━\n"
        f"🔮 <b>LumenSupport</b>\n"
        f"━━━━━━ 💜 ━━━━━━\n\n"
        f"Добро пожаловать в нашу службу поддержки! 🟣\n\n"
        f"Мы здесь, чтобы решить любые ваши вопросы.\n"
        f"Наша команда работает быстро и эффективно.\n\n"
        f"👇 Нажмите на кнопку ниже, чтобы начать:"
    )
    await message.answer(text, reply_markup=main_menu_kb())

# 2. Нажатие на кнопку "Написать в поддержку"
@router.callback_query(F.data == "create_ticket")
async def process_create_ticket(callback: CallbackQuery, state: FSMContext):
    text = (
        f"🟣 <b>Опишите вашу проблему или вопрос.</b>\n\n"
        f"Вы можете отправить текст, фото, видео или документ.\n"
        f"Мы ответим вам в ближайшее время.\n\n"
        f"🔮 <i>Ожидаем ваше сообщение...</i>\n\n"
        f"❌ Для отмены нажмите /cancel"
    )
    await callback.message.edit_text(text)
    await state.set_state(SupportStates.waiting_for_message)
    await callback.answer()

# 3. Команда отмены
@router.message(Command("cancel"))
@router.message(F.text == "❌ Отмена")
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.answer(
        "💜 Действие отменено.\n\n"
        "Вы вернулись в главное меню.", 
        reply_markup=main_menu_kb()
    )

# 4. Пользователь отправляет сообщение (любое: текст, фото, файл)
@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username
    
    # Формируем ссылку на пользователя
    if username:
        user_link = f"@{username}"
    else:
        user_link = f"<a href='tg://user?id={user_id}'>Без username</a>"

    # Уведомляем пользователя
    await message.answer(
        "━━━━━━ 💜 ━━━━━━\n"
        "✅ <b>Обращение принято!</b>\n"
        "━━━━━━ 💜 ━━━━━━\n\n"
        "🔮 Мы уже получили ваше сообщение.\n"
        "Ожидайте ответа от команды LumenSupport."
    )

    # Формируем текст для админа
    admin_text = (
        f"━━━━━━ 💜 ━━━━━━\n"
        f"🔮 <b>LumenSupport</b> | Новое обращение\n"
        f"━━━━━━ 💜 ━━━━━━\n\n"
        f"👤 <b>Пользователь:</b> {user_link}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code>\n\n"
        f"💬 <b>Сообщение:</b>"
    )

    # Пересылаем сообщение админу
    try:
        msg_to_admin = await message.copy_to(
            chat_id=ADMIN_ID, 
            caption=admin_text
        )
        # Сохраняем в словарь, чтобы потом понять, кому отвечать
        ticket_map[msg_to_admin.message_id] = user_id
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")

# 5. Админ отвечает на сообщение пользователя
@router.message(F.from_user.id == ADMIN_ID, F.reply_to_message)
async def admin_reply(message: Message):
    replied_msg_id = message.reply_to_message.message_id
    
    # Проверяем, есть ли это сообщение в нашем словаре обращений
    if replied_msg_id in ticket_map:
        user_id = ticket_map[replied_msg_id]
        
        # Пытаемся отправить ответ пользователю
        try:
            await message.copy_to(
                chat_id=user_id, 
                caption="━━━━━━ 💜 ━━━━━━\n💜 <b>Ответ от LumenSupport</b>\n━━━━━━ 💜 ━━━━━━"
            )
            await message.answer("✅ <i>Ответ успешно доставлен пользователю.</i>")
        except Exception as e:
            await message.answer(
                f"❌ <b>Не удалось доставить ответ!</b>\n"
                f"Возможно, пользователь заблокировал бота.\n\n"
                f"<code>{e}</code>"
            )
        
        # Удаляем тикет из словаря, так как он закрыт
        del ticket_map[replied_msg_id]
    else:
        # Если админ ответил на какое-то другое (не наше) сообщение
        pass

# ==================== ЗАПУСК ====================
async def main():
    logging.info("💜 LumenSupport Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот остановлен.")
