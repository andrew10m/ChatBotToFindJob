# Функции для форматирования текста, генерации сообщений и т.д.

def format_vacancy_for_ работодателя(vacancy_data: dict) -> str:
    """Форматирует данные вакансии для просмотра работодателем."""
    # TODO: Добавить больше деталей, статус и т.д.
    return (
        f"📝 **Название:** {vacancy_data.get('title', 'Не указано')}\n"
        f"📄 **Описание:** {vacancy_data.get('description', 'Не указано')}\n"
        f"💰 **Зарплата:** {vacancy_data.get('salary', 'Не указана')}\n"
        f"📞 **Контакты:** {vacancy_data.get('contact_info', 'Не указаны')}\n"
        f"📊 **Статус:** {vacancy_data.get('status', 'Неизвестен')}\n"
        f"📅 **Создана:** {vacancy_data.get('created_at', 'Неизвестно')}"
    )

def format_vacancy_for_соискателя(vacancy_data: dict) -> str:
    """Форматирует данные вакансии для просмотра соискателем."""
    # TODO: Добавить больше деталей
    return (
        f"📝 **Название:** {vacancy_data.get('title', 'Не указано')}\n"
        f"🏢 **Компания/Работодатель:** (будет информация о работодателе)\n"
        f"📄 **Описание:** {vacancy_data.get('description', 'Не указано')}\n"
        f"💰 **Зарплата:** {vacancy_data.get('salary', 'Не указана')}\n"
        # Контакты работодателя напрямую не показываем до отклика или в зависимости от настроек
    )

def format_application_for_работодателя(application_data: dict, applicant_data: dict) -> str:
    """Форматирует данные отклика для просмотра работодателем."""
    return (
        f"👤 **Соискатель:** {applicant_data.get('username', 'Аноним')} (ID: {application_data.get('applicant_id')})\n"
        f"📄 **Резюме/Сообщение:**\n{application_data.get('resume', 'Нет данных')}\n"
        f"📞 **Контакты соискателя:** {application_data.get('contact_info', 'Не указаны')}\n"
        f"📅 **Откликнулся:** {application_data.get('applied_at', 'Неизвестно')}"
    )

# Другие утилиты для текста...
