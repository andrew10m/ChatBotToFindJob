import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_FALLBACK_TOKEN_HERE") # Replace with your bot token
DATABASE_URL = "job_bot.db" # SQLite database file
ADMIN_TELEGRAM_IDS = [123456789] # Replace with actual admin Telegram IDs

# For pagination
VACANCIES_PER_PAGE = 5

# Conversation states (can be defined here or in the main bot file)
# These are just examples, you might use integers or more descriptive strings
CHOOSE_ROLE, REGISTER_AGREEMENT, POST_VACANCY_FLOW, APPLY_FLOW = range(4)

# Placeholder texts for agreements (in Russian)
# IMPORTANT: These are placeholders. Consult a legal professional for actual text.
GENERAL_USER_AGREEMENT_TEXT = """
**Общее Пользовательское Соглашение**

1.  **Общие положения**
    1.1. Настоящее Пользовательское соглашение (далее – «Соглашение») регулирует отношения между владельцем бота «JobLink Helper» (далее – «Платформа») и Пользователем (Работодателем или Соискателем).
    1.2. Платформа предоставляет техническую возможность для размещения вакансий Работодателями и поиска вакансий Соискателями.
    1.3. Регистрируясь в боте, Пользователь полностью и безоговорочно принимает условия настоящего Соглашения. Если Пользователь не согласен с условиями Соглашения, он не должен использовать Платформу.

2.  **Предмет Соглашения**
    2.1. Платформа является исключительно информационным посредником, облегчающим контакт между Работодателями и Соискателями.
    2.2. Платформа не является стороной каких-либо трудовых или иных договоров, заключаемых между Пользователями. Все договоренности достигаются и исполняются Пользователями самостоятельно и под свою ответственность.

3.  **Права и обязанности Сторон**
    3.1. Пользователь обязуется предоставлять достоверную информацию при регистрации и использовании Платформы.
    3.2. Пользователь обязуется соблюдать действующее законодательство Российской Федерации, включая, но не ограничиваясь, Федеральный закон № 152-ФЗ «О персональных данных».
    3.3. Пользователь самостоятельно несет ответственность за содержание размещаемой им информации.
    3.4. Платформа имеет право модерировать и удалять информацию, нарушающую данное Соглашение или законодательство РФ.

4.  **Ответственность и ограничение ответственности**
    4.1. Платформа не несет ответственности за любые споры, убытки, ущерб (включая моральный вред), возникшие в результате взаимодействия Пользователей, включая, но не ограничиваясь, вопросы неоплаты услуг, производственных травм, краж, мошенничества или иных противоправных действий.
    4.2. Платформа не гарантирует трудоустройство Соискателей или нахождение подходящих кандидатов Работодателями.
    4.3. Платформа предоставляется «как есть». Владелец Платформы не несет ответственности за временные сбои и перерывы в работе Платформы.

5.  **Обработка персональных данных**
    5.1. Регистрируясь и используя Платформу, Пользователь дает свое согласие на обработку своих персональных данных в соответствии с Политикой конфиденциальности (прилагается или доступна по ссылке [TODO: Add Link]) и Федеральным законом № 152-ФЗ «О персональных данных».
    5.2. Согласие включает сбор, запись, систематизацию, накопление, хранение, уточнение (обновление, изменение), извлечение, использование, передачу (предоставление, доступ), обезличивание, блокирование, удаление, уничтожение персональных данных.
    5.3. Цель обработки: обеспечение функционирования Платформы, идентификация Пользователей, связь с Пользователями.

6.  **Заключительные положения**
    6.1. Настоящее Соглашение может быть изменено владельцем Платформы в одностороннем порядке. Новая редакция Соглашения вступает в силу с момента ее публикации.
    6.2. Все споры решаются путем переговоров. При недостижении согласия споры подлежат разрешению в соответствии с законодательством РФ.

**Принимая это соглашение, вы подтверждаете, что ознакомлены и согласны со всеми пунктами.**
"""

VACANCY_APPLICATION_AGREEMENT_TEXT = """
**Соглашение по Отклику на Вакансию**

1.  Настоящим я, Соискатель, подтверждаю свое намерение откликнуться на выбранную вакансию через платформу «JobLink Helper».
2.  Я понимаю и соглашаюсь с тем, что платформа «JobLink Helper» является лишь информационным посредником и не является моим работодателем или агентом.
3.  Все условия потенциального трудоустройства, включая, но не ограничиваясь, оплату труда, условия работы, должностные обязанности, социальные гарантии и безопасность на рабочем месте, обсуждаются и согласовываются исключительно между мной и Работодателем, разместившим вакансию.
4.  Платформа «JobLink Helper» и ее владелец не несут ответственности за:
    a.  Достоверность информации, предоставленной Работодателем в описании вакансии.
    b.  Выполнение Работодателем своих обязательств передо мной (например, по оплате труда).
    c.  Обеспечение безопасных условий труда.
    d.  Любые споры, разногласия или инциденты (включая невыплату заработной платы, производственные травмы, незаконные действия), которые могут возникнуть в процессе моего взаимодействия с Работодателем или в ходе выполнения трудовых обязанностей.
5.  Я обязуюсь самостоятельно проверять информацию о Работодателе и условиях труда перед заключением каких-либо соглашений.
6.  Я даю согласие на передачу моих контактных данных и резюме/сообщения Работодателю, на чью вакансию я откликаюсь.

**Принимая это соглашение, вы подтверждаете, что понимаете и согласны с тем, что все трудовые отношения возникают непосредственно между вами и работодателем, и платформа не несет за них ответственности.**
"""
# States for ConversationHandler (more granular as per bot_handlers_design.txt)
(
    CHOOSE_ROLE,
    REGISTER_EMPLOYER_AGREEMENT,
    REGISTER_JOB_SEEKER_AGREEMENT,
    EMPLOYER_ACTIONS,
    JOB_SEEKER_ACTIONS,
    ADMIN_ACTIONS,
    POST_VACANCY_TITLE,
    POST_VACANCY_DESCRIPTION,
    POST_VACANCY_SALARY,
    POST_VACANCY_CONTACTS,
    POST_VACANCY_CONFIRM,
    VIEW_VACANCIES_LIST,
    APPLY_VACANCY_CONFIRM_AGREEMENT,
    APPLY_VACANCY_SUBMIT_INFO,
    FILTER_VACANCIES_KEYWORDS,
    MODERATE_VACANCY_ID,
    CONFIRM_GENERAL_AGREEMENT # General agreement confirmation state
) = range(17) # Ensure this number matches the number of states

# Callback data prefixes
CALLBACK_ROLE_EMPLOYER = "role_employer"
CALLBACK_ROLE_JOB_SEEKER = "role_job_seeker"
CALLBACK_ACCEPT_GENERAL_AGREEMENT = "accept_general_agreement"
CALLBACK_DECLINE_GENERAL_AGREEMENT = "decline_general_agreement"
CALLBACK_POST_VACANCY = "post_vacancy"
CALLBACK_MY_VACANCIES = "my_vacancies"
CALLBACK_VIEW_APPLICATIONS = "view_applications_employer" # More specific
CALLBACK_VIEW_VACANCIES_JS = "view_vacancies_js"
CALLBACK_MY_APPLICATIONS_JS = "my_applications_js"
CALLBACK_FILTER_VACANCIES_JS = "filter_vacancies_js"
CALLBACK_VACANCY_DETAILS_PREFIX = "vac_details_"
CALLBACK_VACANCY_APPLY_PREFIX = "vac_apply_"
CALLBACK_ACCEPT_VACANCY_AGREEMENT = "accept_vac_agreement_" # Append vacancy_id
CALLBACK_DECLINE_VACANCY_AGREEMENT = "decline_vac_agreement_" # Append vacancy_id
CALLBACK_PUBLISH_VACANCY = "publish_vacancy"
CALLBACK_EDIT_VACANCY_FROM_CONFIRM = "edit_vacancy_from_confirm" # Placeholder
CALLBACK_CANCEL_VACANCY_POST = "cancel_vacancy_post"
CALLBACK_NAV_VACANCIES_NEXT = "nav_vac_next_" # Append offset
CALLBACK_NAV_VACANCIES_PREV = "nav_vac_prev_" # Append offset

# Admin Callbacks
CALLBACK_MODERATE_VACANCIES = "admin_moderate_vacs"
CALLBACK_APPROVE_VACANCY = "admin_approve_vac_" # Append vacancy_id
CALLBACK_REJECT_VACANCY = "admin_reject_vac_" # Append vacancy_id


# Message texts (Russian) - Grouped for easier management
TEXTS_RU = {
    "welcome_new_user": "Добро пожаловать! Пожалуйста, выберите вашу роль:",
    "welcome_back_employer": "С возвращением, Работодатель! Что бы вы хотели сделать?",
    "welcome_back_job_seeker": "С возвращением, Соискатель! Что бы вы хотели сделать?",
    "welcome_admin": "Панель администратора.",
    "role_selection_prompt": "Кто вы?",
    "employer_button": "Я Работодатель",
    "job_seeker_button": "Я Соискатель",
    "general_agreement_prompt": "Пожалуйста, ознакомьтесь с Пользовательским соглашением и примите его условия для продолжения.",
    "accept_button": "✅ Принимаю",
    "decline_button": "❌ Отклоняю",
    "agreement_declined_message": "К сожалению, без принятия соглашения вы не можете использовать бота. Нажмите /start для повторной попытки.",
    "registration_complete_employer": "Регистрация как Работодатель завершена! Теперь вы можете публиковать вакансии.",
    "registration_complete_job_seeker": "Регистрация как Соискатель завершена! Теперь вы можете искать вакансии.",
    "action_canceled": "Действие отменено.",
    "help_message": "Доступные команды:\n/start - Начать/перезапустить бота\n/help - Показать это сообщение\n/cancel - Отменить текущее действие",

    "employer_menu_prompt": "Меню Работодателя:",
    "post_vacancy_button": "Опубликовать вакансию",
    "my_vacancies_button": "Мои вакансии",
    "view_applications_button": "Просмотреть отклики",

    "job_seeker_menu_prompt": "Меню Соискателя:",
    "view_vacancies_button": "Смотреть вакансии",
    "my_applications_button": "Мои отклики",
    "filter_vacancies_button": "Фильтр вакансий",

    "admin_menu_prompt": "Меню Администратора:",
    "moderate_vacancies_button": "Модерация вакансий",
    "manage_users_button": "Управление пользователями (TBD)",

    "enter_vacancy_title": "Введите название вакансии:",
    "enter_vacancy_description": "Введите описание вакансии:",
    "enter_vacancy_salary": "Укажите зарплату (например, '50000 руб.' или 'от 80000 до 120000 руб.'):",
    "enter_vacancy_contacts": "Введите контактные данные для этой вакансии (например, Telegram @username или телефон):",
    "vacancy_confirm_prompt": "Проверьте данные вакансии:\n\nНазвание: {title}\nОписание: {description}\nЗарплата: {salary}\nКонтакты: {contacts}\n\nВсе верно?",
    "publish_button": "✅ Опубликовать",
    "edit_button": "✏️ Редактировать", # Simplified: "✏️ Начать заново"
    "cancel_button": "❌ Отменить",
    "vacancy_published_moderation": "Вакансия отправлена на модерацию!",
    "vacancy_published_active": "Вакансия опубликована!",
    "vacancy_publication_cancelled": "Публикация вакансии отменена.",
    "restart_vacancy_posting": "Хорошо, давайте начнем заново. Введите название вакансии:",

    "no_active_vacancies": "На данный момент активных вакансий нет.",
    "vacancy_details_application_prompt": "Для отклика на эту вакансию, пожалуйста, примите 'Соглашение по Отклику на Вакансию'.",
    "vacancy_application_agreement_prompt": "Ознакомьтесь с 'Соглашением по Отклику на Вакансию' и примите его:",
    "accept_and_apply_button": "✅ Принимаю и Откликнуться",
    "back_to_list_button": "❌ Назад к списку",
    "send_resume_or_message_prompt": "Пожалуйста, отправьте ваше резюме (как файл) или короткое сообщение о себе для работодателя. Вы также можете просто нажать 'Отправить контактные данные', чтобы работодатель связался с вами.",
    "submit_contact_info_button": "Отправить мои контакты",
    "application_sent": "Ваш отклик отправлен!",
    "application_failed": "Не удалось отправить отклик. Попробуйте позже.",
    "new_application_notification_employer": "Новый отклик на вашу вакансию '{vacancy_title}' от пользователя {user_mention}.",

    "enter_keywords_for_filter": "Введите ключевые слова для поиска (например, 'python разработчик Москва'):",
    "filter_applied": "Фильтр применен. Теперь при просмотре вакансий будут показаны только соответствующие.",
    "clear_filter_button": "Сбросить фильтр",

    "next_page_button": "Следующие >>",
    "prev_page_button": "<< Предыдущие",
    "error_generic": "Произошла ошибка. Попробуйте еще раз позже. Если проблема сохраняется, свяжитесь с администратором.",
    "command_unknown": "Неизвестная команда. Используйте /help для списка команд."
}
