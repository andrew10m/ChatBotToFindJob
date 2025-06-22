-- Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER UNIQUE NOT NULL,
    user_type TEXT NOT NULL CHECK (user_type IN ('employer', 'job_seeker', 'admin')), -- employer, job_seeker, admin
    username TEXT, -- Telegram username, if available
    first_name TEXT,
    last_name TEXT,
    registration_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    general_agreement_accepted BOOLEAN DEFAULT FALSE,
    general_agreement_timestamp DATETIME
);

-- Vacancies Table
CREATE TABLE IF NOT EXISTS vacancies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    salary TEXT, -- Can be a range or specific amount
    contact_details TEXT NOT NULL,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'closed', 'pending_moderation')), -- active, closed, pending_moderation
    creation_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employer_id) REFERENCES users (id)
);

-- Applications Table
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_seeker_id INTEGER NOT NULL,
    vacancy_id INTEGER NOT NULL,
    resume_or_message TEXT, -- Could be path to a file or text message
    application_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    vacancy_agreement_accepted BOOLEAN DEFAULT FALSE,
    vacancy_agreement_timestamp DATETIME,
    FOREIGN KEY (job_seeker_id) REFERENCES users (id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies (id)
);

-- User_Agreements_Log Table (Optional but good for detailed tracking if needed beyond user table flags)
-- This table can log every instance of agreement acceptance if there are versions or more complex scenarios.
-- For the current scope, boolean flags in `users` and `applications` tables are sufficient.
-- However, for robust legal tracking, especially if agreements change version, this would be useful.
/*
CREATE TABLE IF NOT EXISTS user_agreements_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    agreement_type TEXT NOT NULL CHECK (agreement_type IN ('general', 'vacancy_application')), -- general, vacancy_application
    agreement_version TEXT, -- If agreements are versioned
    acceptance_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    related_id INTEGER, -- e.g., vacancy_id for vacancy_application agreement
    FOREIGN KEY (user_id) REFERENCES users (id)
);
*/

-- Admin_Log Table (For tracking admin actions, optional for initial scope)
/*
CREATE TABLE IF NOT EXISTS admin_actions_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL, -- e.g., 'moderate_vacancy', 'delete_user'
    target_id INTEGER, -- e.g., vacancy_id, user_id
    action_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    details TEXT,
    FOREIGN KEY (admin_id) REFERENCES users (id)
);
*/

-- Categories Table (Optional, for filtering vacancies)
/*
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS vacancy_categories (
    vacancy_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (vacancy_id, category_id),
    FOREIGN KEY (vacancy_id) REFERENCES vacancies (id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);
*/

PRAGMA foreign_keys = ON;
