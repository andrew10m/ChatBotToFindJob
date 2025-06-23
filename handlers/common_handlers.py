from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.inline_keyboards import start_agreement_keyboard, choose_role_keyboard
from db import queries as db_queries # Импортируем запросы к БД
from states.user_states import RegistrationStates
from config import USER_AGREEMENT_PATH, PRIVACY_POLICY_PATH, DISCLAIMER_NOTICE_PATH

router = Router()

async def read_document(file_path: str) -> str:
    """Читает текстовый файл и возвращает его содержимое."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return "Документ не найден."
    except Exception as e:
        return f"Ошибка при чтении документа: {e}"

WELCOME_TEXT = """👋 **Добро пожаловать в JobBot!**

Я помогу вам разместить вакансии или найти работу.

Прежде чем мы начнем, пожалуйста, ознакомьтесь с нашими правилами:
- **Пользовательское соглашение** (определяет правила использования бота)
- **Политика конфиденциальности** (как мы обрабатываем ваши данные)

Нажимая «✅ Принять условия и продолжить», вы подтверждаете, что прочитали и согласны с этими документами, а также даете согласие на обработку ваших персональных данных.

Вы также можете прочитать **Уведомление об ограничении ответственности** (важная информация о роли платформы).
"""

DISCLAIMER_TEXT_SHORT = "JobBot является информационной платформой и не несет ответственности за договоренности между пользователями. Подробнее: /about или кнопка ниже."

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user = await db_queries.get_user(user_id)

    if user and user['accepted_terms']:
        await message.answer(f"С возвращением, {message.from_user.first_name}! Вы уже приняли условия. Воспользуйтесь /menu для навигации.")
        # Тут можно сразу перевести в главное меню, если пользователь уже зарегистрирован и выбрал роль
        # Например, если user['role'] уже установлен.
        if user['role']:
            # TODO: Перенаправить в соответствующее меню в зависимости от роли
            await message.answer(f"Ваша роль: {user['role']}. Главное меню доступно по команде /menu.")
        else:
            # Если роль еще не выбрана (маловероятно, если accepted_terms=True, но для подстраховки)
            await message.answer("Пожалуйста, выберите вашу роль:", reply_markup=choose_role_keyboard())
            await state.set_state(RegistrationStates.choosing_role)
        return

    # Если пользователь новый или не принял условия
    await message.answer(WELCOME_TEXT + "\n\n" + DISCLAIMER_TEXT_SHORT, reply_markup=start_agreement_keyboard(), parse_mode="Markdown")
    # Можно установить состояние ожидания принятия условий, если это необходимо для сложной логики
    # await state.set_state(RegistrationStates.new_user_awaiting_agreement)


@router.callback_query(F.data == "read_terms")
async def cq_read_terms(callback: CallbackQuery):
    terms_text = await read_document(USER_AGREEMENT_PATH)
    # Отправляем длинный текст частями, если он превышает лимиты Telegram
    # Для простоты пока отправляем как есть, но в продакшене нужно делить
    # или использовать Telegraph для статей.
    await callback.message.answer("📜 **Пользовательское соглашение JobBot** (начало):\n\n" + terms_text[:4000], parse_mode="Markdown")
    if len(terms_text) > 4000:
         await callback.message.answer(terms_text[4000:8000], parse_mode="Markdown") # И так далее
    await callback.answer()

@router.callback_query(F.data == "read_privacy")
async def cq_read_privacy(callback: CallbackQuery):
    privacy_text = await read_document(PRIVACY_POLICY_PATH)
    await callback.message.answer("🔒 **Политика конфиденциальности JobBot** (начало):\n\n" + privacy_text[:4000], parse_mode="Markdown")
    if len(privacy_text) > 4000:
        await callback.message.answer(privacy_text[4000:8000], parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "read_disclaimer_start") # Новая кнопка
async def cq_read_disclaimer_start(callback: CallbackQuery):
    disclaimer_text = await read_document(DISCLAIMER_NOTICE_PATH)
    await callback.message.answer("📄 **Уведомление об ограничении ответственности**:\n\n" + disclaimer_text, parse_mode="Markdown")
    await callback.answer()


@router.callback_query(F.data == "accept_terms")
async def cq_accept_terms(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    username = callback.from_user.username

    # Проверяем, есть ли пользователь в БД
    user = await db_queries.get_user(user_id)
    if not user:
        # Создаем пользователя с временной ролью или без роли, пока не выберет
        # accepted_terms будет обновлен чуть позже
        await db_queries.create_user(user_id, role="unknown", username=username, accepted_terms=False) # Временно 'unknown'
        # Логируем принятие общего соглашения
        await db_queries.log_agreement(user_id, agreement_type='general_terms')
        await db_queries.log_agreement(user_id, agreement_type='privacy_policy') # Также логируем принятие политики
        await db_queries.update_user_accepted_terms(user_id, accepted=True)
        await callback.message.edit_text(
            "Спасибо! Вы приняли условия. Теперь выберите вашу роль:",
            reply_markup=choose_role_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_role)
    elif not user['accepted_terms']:
        await db_queries.log_agreement(user_id, agreement_type='general_terms')
        await db_queries.log_agreement(user_id, agreement_type='privacy_policy')
        await db_queries.update_user_accepted_terms(user_id, accepted=True)
        await callback.message.edit_text(
            "Спасибо! Вы обновили свое согласие с условиями. Теперь выберите вашу роль (если еще не выбрали):",
            reply_markup=choose_role_keyboard()
        )
        await state.set_state(RegistrationStates.choosing_role) # Даже если роль есть, даем выбрать снова, или проверяем user['role']
    else:
        # Пользователь уже принял условия, возможно, нажал кнопку еще раз
        await callback.message.edit_text(
            "Вы уже приняли условия. Пожалуйста, выберите вашу роль, если не сделали этого ранее, или используйте /menu.",
            reply_markup=choose_role_keyboard() if not user['role'] or user['role'] == 'unknown' else None
        )
        if not user['role'] or user['role'] == 'unknown':
            await state.set_state(RegistrationStates.choosing_role)
        # Если роль уже есть, можно ничего не делать или перенаправить в меню
    await callback.answer()


@router.callback_query(F.data == "decline_terms")
async def cq_decline_terms(callback: CallbackQuery, state: FSMContext):
    await db_queries.update_user_accepted_terms(callback.from_user.id, accepted=False) # Если пользователь был, но отозвал
    await callback.message.edit_text(
        "Вы отказались принять условия. К сожалению, без этого вы не можете использовать JobBot. "
        "Если вы передумаете, просто нажмите /start снова."
    )
    await state.clear() # Сбрасываем состояние
    await callback.answer()


@router.callback_query(RegistrationStates.choosing_role, F.data.startswith("role_"))
async def cq_choose_role(callback: CallbackQuery, state: FSMContext):
    role = callback.data.split("_")[1] # employer или job_seeker
    user_id = callback.from_user.id

    await db_queries.update_user_role(user_id, role)
    # Здесь можно запросить контактную информацию, если это требуется сразу после выбора роли
    # await state.set_state(RegistrationStates.entering_contact_info)
    # await callback.message.edit_text(f"Вы выбрали роль: {'Работодатель' if role == 'employer' else 'Соискатель'}.\n"
    #                                 "Теперь, пожалуйста, укажите ваши контактные данные (например, email или телефон). "
    #                                 "Эта информация будет использоваться для связи с вами.")

    # Пока просто завершаем регистрацию роли
    await callback.message.edit_text(
        f"Отлично! Ваша роль: **{'Работодатель' if role == 'employer' else 'Соискатель'}**.\n"
        f"Теперь вы можете пользоваться функциями бота. Используйте команду /menu для навигации."
    )
    await state.clear()
    await callback.answer()


# TODO: Добавить обработчик для RegistrationStates.entering_contact_info
# @router.message(RegistrationStates.entering_contact_info, F.text)
# async def process_contact_info(message: Message, state: FSMContext):
#     contact_info = message.text
#     user_id = message.from_user.id
#     await db_queries.update_user_contact_info(user_id, contact_info)
#     await message.answer("Контактная информация сохранена! Регистрация завершена. Используйте /menu.")
#     await state.clear()


@router.message(Command(commands=["menu"]))
async def cmd_menu(message: Message):
    # Логика для /menu будет здесь
    # - Определение роли пользователя
    # - Отображение соответствующего меню
    await message.answer("Привет! Это заглушка для команды /menu.")

@router.message(Command(commands=["terms"]))
async def cmd_terms(message: Message):
    # Логика для /terms (Пользовательское соглашение)
    await message.answer("Здесь будет текст Пользовательского соглашения.")

@router.message(Command(commands=["privacy"]))
async def cmd_privacy(message: Message):
    # Логика для /privacy (Политика конфиденциальности)
    await message.answer("Здесь будет текст Политики конфиденциальности.")

@router.message(Command(commands=["rules"]))
async def cmd_rules(message: Message):
    # Логика для /rules (Правила модерации)
    await message.answer("Здесь будут текст Правил модерации.")

@router.message(Command(commands=["about"]))
async def cmd_about(message: Message):
    # Логика для /about (О платформе и ограничение ответственности)
    await message.answer("Здесь будет информация о платформе и уведомление об ограничении ответственности.")

@router.message(Command(commands=["profile"]))
async def cmd_profile(message: Message):
    # Логика для /profile (роль, контакты, рейтинг)
    await message.answer("Здесь будет информация вашего профиля.")

@router.message(Command(commands=["appeal"]))
async def cmd_appeal(message: Message):
    # Логика для /appeal (Апелляция для отклоненных вакансий)
    await message.answer("Здесь будет форма для подачи апелляции.")

# Другие общие обработчики (например, для колбеков от общих кнопок) могут быть здесь.
