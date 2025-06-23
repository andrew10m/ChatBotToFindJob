-- Схема базы данных для JobBot

-- Пользователи
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY, -- Telegram User ID
    role TEXT NOT NULL CHECK(role IN ('employer', 'job_seeker', 'admin')), -- Роль пользователя
    username TEXT, -- Telegram username (может быть NULL)
    contact_info TEXT, -- Контактная информация, предоставленная пользователем
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Дата и время регистрации
    accepted_terms BOOLEAN DEFAULT FALSE, -- Принял ли пользователь общие условия
    is_blocked BOOLEAN DEFAULT FALSE -- Заблокирован ли пользователь
);

-- Вакансии
CREATE TABLE IF NOT EXISTS vacancies (
    vacancy_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL, -- user_id работодателя
    title TEXT NOT NULL, -- Название вакансии
    description TEXT NOT NULL, -- Описание вакансии
    salary TEXT, -- Зарплата (может быть текстовым полем для гибкости, например, "от 1000 USD" или "по договоренности")
    contact_info TEXT NOT NULL, -- Контакты для связи по вакансии
    status TEXT NOT NULL DEFAULT 'pending_moderation' CHECK(status IN ('pending_moderation', 'active', 'closed', 'rejected')), -- Статус вакансии
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Дата и время создания
    moderator_message TEXT, -- Сообщение от модератора (например, причина отклонения)
    FOREIGN KEY (employer_id) REFERENCES users(user_id)
);

-- Отклики на вакансии
CREATE TABLE IF NOT EXISTS applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    vacancy_id INTEGER NOT NULL,
    applicant_id INTEGER NOT NULL, -- user_id соискателя
    resume TEXT NOT NULL, -- Текст резюме или сопроводительного письма
    contact_info TEXT NOT NULL, -- Контактная информация соискателя для этого отклика
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'viewed', 'accepted', 'rejected')), -- Статус отклика
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id),
    FOREIGN KEY (applicant_id) REFERENCES users(user_id)
);

-- Логи модерации
CREATE TABLE IF NOT EXISTS moderation_logs (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL, -- user_id администратора
    vacancy_id INTEGER, -- ID модерируемой вакансии (может быть NULL, если блокировка пользователя)
    target_user_id INTEGER, -- ID пользователя, к которому применяется действие (например, блокировка)
    action TEXT NOT NULL CHECK(action IN ('approve_vacancy', 'reject_vacancy', 'block_user', 'unblock_user')), -- Действие модератора
    reason TEXT, -- Причина действия
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(user_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id),
    FOREIGN KEY (target_user_id) REFERENCES users(user_id)
);

-- Рейтинги
CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rater_id INTEGER NOT NULL, -- user_id того, кто ставит оценку
    rated_id INTEGER NOT NULL, -- user_id того, кому ставят оценку (может быть работодателем или соискателем)
    vacancy_id INTEGER, -- ID вакансии, в контексте которой ставится оценка (опционально, но рекомендуется)
    score INTEGER NOT NULL CHECK(score >= 1 AND score <= 5), -- Оценка от 1 до 5
    comment TEXT, -- Комментарий к оценке
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rater_id) REFERENCES users(user_id),
    FOREIGN KEY (rated_id) REFERENCES users(user_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id)
);

-- Соглашения
CREATE TABLE IF NOT EXISTS agreements (
    agreement_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    agreement_type TEXT NOT NULL CHECK(agreement_type IN ('general_terms', 'privacy_policy', 'vacancy_application')), -- Тип соглашения
    vacancy_id INTEGER, -- ID вакансии, если agreement_type = 'vacancy_application'
    accepted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies(vacancy_id)
);

-- Индексы для ускорения часто используемых запросов
CREATE INDEX IF NOT EXISTS idx_vacancies_status ON vacancies(status);
CREATE INDEX IF NOT EXISTS idx_vacancies_employer_id ON vacancies(employer_id);
CREATE INDEX IF NOT EXISTS idx_applications_vacancy_id ON applications(vacancy_id);
CREATE INDEX IF NOT EXISTS idx_applications_applicant_id ON applications(applicant_id);
CREATE INDEX IF NOT EXISTS idx_ratings_rated_id ON ratings(rated_id);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
