from aiogram.fsm.state import State, StatesGroup

class RegistrationStates(StatesGroup):
    choosing_role = State()
    entering_contact_info = State()
    # new_user_awaiting_agreement = State() # Для тех, кто сначала отказался, потом решил принять

class VacancyCreationStates(StatesGroup):
    entering_title = State()
    entering_description = State()
    entering_salary = State()
    entering_contacts = State()
    confirming_vacancy = State()

class ApplicationStates(StatesGroup):
    entering_resume = State()
    entering_contacts = State()
    confirming_application = State()

class ModerationStates(StatesGroup):
    rejecting_vacancy_reason = State() # Для ввода причины отклонения
    blocking_user_reason = State() # Для ввода причины блокировки

class AppealStates(StatesGroup):
    entering_appeal_text = State()

# Другие группы состояний по мере необходимости...
