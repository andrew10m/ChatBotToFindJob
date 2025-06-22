import sqlite3
import logging
from datetime import datetime

DATABASE_URL = "job_bot.db"

# Basic Logging Setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    # Enable foreign key constraint enforcement for SQLite
    if conn:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as e:
            logger.error(f"Failed to enable foreign keys for SQLite: {e}")
    return conn

def init_db():
    """Initializes the database by creating tables from the schema."""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("Failed to get DB connection for init_db.")
            return

        cursor = conn.cursor()
        with open('database_schema.sql', 'r') as f:
            schema = f.read()
        cursor.executescript(schema)
        conn.commit()
        logger.info("Database initialized successfully.")
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        conn.close()

# --- User Management ---
def create_user(telegram_id: int, user_type: str, username: str = None, first_name: str = None, last_name: str = None) -> int:
    """Creates a new user or updates user_type if they already exist but hadn't chosen a role."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (telegram_id, user_type, username, first_name, last_name, registration_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                user_type=excluded.user_type,
                username=excluded.username,
                first_name=excluded.first_name,
                last_name=excluded.last_name
            WHERE users.user_type IS NULL OR users.user_type = '';
        """, (telegram_id, user_type, username, first_name, last_name, datetime.now()))
        conn.commit()
        user_id = cursor.lastrowid
        if not user_id: # If ON CONFLICT DO UPDATE happened on an existing user, get their ID
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_record = cursor.fetchone()
            if user_record:
                user_id = user_record['id']
        logger.info(f"User {telegram_id} created/updated as {user_type}. DB ID: {user_id}")
        return user_id
    except sqlite3.Error as e:
        logger.error(f"Error creating/updating user {telegram_id}: {e}")
        return None
    finally:
        conn.close()

def get_user(telegram_id: int):
    """Retrieves a user by their Telegram ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        logger.error(f"Error retrieving user {telegram_id}: {e}")
        return None
    finally:
        conn.close()

def set_general_agreement_accepted(telegram_id: int, accepted: bool):
    """Updates the general agreement acceptance status for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        timestamp = datetime.now() if accepted else None
        cursor.execute("""
            UPDATE users
            SET general_agreement_accepted = ?, general_agreement_timestamp = ?
            WHERE telegram_id = ?
        """, (accepted, timestamp, telegram_id))
        conn.commit()
        logger.info(f"General agreement status for user {telegram_id} set to {accepted}.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating general agreement for user {telegram_id}: {e}")
        return False
    finally:
        conn.close()

# --- Vacancy Management ---
def create_vacancy(employer_id: int, title: str, description: str, salary: str, contact_details: str, status: str = 'pending_moderation') -> int:
    """Creates a new vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO vacancies (employer_id, title, description, salary, contact_details, status, creation_timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employer_id, title, description, salary, contact_details, status, datetime.now()))
        conn.commit()
        vacancy_id = cursor.lastrowid
        logger.info(f"Vacancy '{title}' created by employer_id {employer_id}. DB ID: {vacancy_id}")
        return vacancy_id
    except sqlite3.Error as e:
        logger.error(f"Error creating vacancy '{title}': {e}")
        return None
    finally:
        conn.close()

def get_vacancy_by_id(vacancy_id: int):
    """Retrieves a specific vacancy by its ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT v.*, u.username as employer_username FROM vacancies v JOIN users u ON v.employer_id = u.id WHERE v.id = ?", (vacancy_id,))
        vacancy = cursor.fetchone()
        return vacancy
    except sqlite3.Error as e:
        logger.error(f"Error retrieving vacancy {vacancy_id}: {e}")
        return None
    finally:
        conn.close()

def get_active_vacancies(limit: int = 5, offset: int = 0, keywords: str = None):
    """Retrieves active vacancies, optionally filtered by keywords, with pagination."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        query = "SELECT v.*, u.username as employer_username FROM vacancies v JOIN users u ON v.employer_id = u.id WHERE v.status = 'active'"
        params = []
        if keywords:
            # Simple keyword search in title and description
            keyword_tokens = keywords.split()
            for token in keyword_tokens:
                query += " AND (v.title LIKE ? OR v.description LIKE ?)"
                params.extend([f'%{token}%', f'%{token}%'])

        query += " ORDER BY v.creation_timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor.execute(query, tuple(params))
        vacancies = cursor.fetchall()
        return vacancies
    except sqlite3.Error as e:
        logger.error(f"Error retrieving active vacancies: {e}")
        return []
    finally:
        conn.close()

def update_vacancy_status(vacancy_id: int, status: str):
    """Updates the status of a vacancy (e.g., 'active', 'closed', 'pending_moderation')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE vacancies SET status = ? WHERE id = ?", (status, vacancy_id))
        conn.commit()
        logger.info(f"Vacancy {vacancy_id} status updated to {status}.")
        return True
    except sqlite3.Error as e:
        logger.error(f"Error updating status for vacancy {vacancy_id}: {e}")
        return False
    finally:
        conn.close()

# --- Application Management ---
def create_application(employee_id: int, vacancy_id: int, resume_or_message: str, agreement_accepted: bool) -> int: # Renamed job_seeker_id to employee_id
    """Creates a new job application."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        timestamp = datetime.now() if agreement_accepted else None
        cursor.execute("""
            INSERT INTO applications (employee_id, vacancy_id, resume_or_message, vacancy_agreement_accepted, vacancy_agreement_timestamp, application_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (employee_id, vacancy_id, resume_or_message, agreement_accepted, timestamp, datetime.now())) # Renamed job_seeker_id to employee_id
        conn.commit()
        application_id = cursor.lastrowid
        logger.info(f"Application created for vacancy {vacancy_id} by employee_id {employee_id}. DB ID: {application_id}") # Renamed job_seeker_id to employee_id
        return application_id
    except sqlite3.Error as e:
        logger.error(f"Error creating application for vacancy {vacancy_id} by employee_id {employee_id}: {e}") # Renamed job_seeker_id to employee_id
        return None
    finally:
        conn.close()

def get_applications_for_vacancy(vacancy_id: int):
    """Retrieves all applications for a specific vacancy."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT a.*, u.username as employee_username, u.first_name as employee_first_name  -- Renamed seeker_... to employee_...
            FROM applications a
            JOIN users u ON a.employee_id = u.id -- Renamed job_seeker_id to employee_id
            WHERE a.vacancy_id = ?
            ORDER BY a.application_timestamp DESC
        """, (vacancy_id,))
        applications = cursor.fetchall()
        return applications
    except sqlite3.Error as e:
        logger.error(f"Error retrieving applications for vacancy {vacancy_id}: {e}")
        return []
    finally:
        conn.close()

def get_user_applications(job_seeker_id: int):
    """Retrieves all applications submitted by a specific job seeker."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT a.*, v.title as vacancy_title
            FROM applications a
            JOIN vacancies v ON a.vacancy_id = v.id
            WHERE a.employee_id = ? -- Renamed job_seeker_id to employee_id
            ORDER BY a.application_timestamp DESC
        """, (job_seeker_id,)) # Parameter name job_seeker_id kept for clarity in function signature, but refers to employee_id in DB
        applications = cursor.fetchall()
        return applications
    except sqlite3.Error as e:
        logger.error(f"Error retrieving applications for employee_id {job_seeker_id}: {e}") # Renamed job_seeker_id to employee_id
        return []
    finally:
        conn.close()

if __name__ == '__main__':
    # This will initialize the DB if you run this file directly
    # Ensure 'database_schema.sql' is in the same directory or adjust path
    logger.info("Initializing database from utils.py...")
    init_db()
    logger.info("Database initialization attempt complete.")

    # Example Usage (for testing)
    # user_id = create_user(12345, 'employer', 'test_employer')
    # if user_id:
    #     set_general_agreement_accepted(12345, True)
    #     user = get_user(12345)
    #     if user and user['general_agreement_accepted']:
    #         print(f"User {user['username']} accepted general agreement at {user['general_agreement_timestamp']}")
    #         vac_id = create_vacancy(user['id'], "Python Developer", "Mid-level Python dev needed.", "100000 RUB", "@employer_contact", status='active')
    #         if vac_id:
    #             print(f"Vacancy created with ID: {vac_id}")

    # seeker_id = create_user(67890, 'job_seeker', 'test_seeker')
    # if seeker_id:
    #     set_general_agreement_accepted(67890, True)
    #     user_seeker = get_user(67890)
    #     if user_seeker and user_seeker['general_agreement_accepted']:
    #         print(f"User {user_seeker['username']} accepted general agreement.")
    #         # Assuming vac_id from above is valid and active
    #         # app_id = create_application(user_seeker['id'], vac_id, "Here is my resume.", True)
    #         # if app_id:
    #         #     print(f"Application submitted with ID: {app_id}")

    # active_vacs = get_active_vacancies()
    # print(f"Active vacancies: {len(active_vacs)}")
    # for v in active_vacs:
    #     print(f"- {v['title']} by {v['employer_username']}")

    # if active_vacs:
    #     apps = get_applications_for_vacancy(active_vacs[0]['id'])
    #     print(f"Applications for '{active_vacs[0]['title']}': {len(apps)}")
    #     for app in apps:
    #         print(f"  - From: {app['seeker_username']}, Message: {app['resume_or_message']}")

def get_user_by_internal_id(db_id: int):
    """Retrieves a user by their internal database ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (db_id,))
        user = cursor.fetchone()
        return user
    except sqlite3.Error as e:
        logger.error(f"Error retrieving user by internal ID {db_id}: {e}")
        return None
    finally:
        conn.close()

def get_vacancies_by_employer(employer_db_id: int):
    """Retrieves all vacancies posted by a specific employer using their DB ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM vacancies WHERE employer_id = ? ORDER BY creation_timestamp DESC", (employer_db_id,))
        vacancies = cursor.fetchall()
        return vacancies
    except sqlite3.Error as e:
        logger.error(f"Error retrieving vacancies for employer ID {employer_db_id}: {e}")
        return []
    finally:
        conn.close()

def get_vacancies_by_status(status: str, limit: int = 10, offset: int = 0):
    """Retrieves vacancies by their status (e.g., 'pending_moderation')."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT v.*, u.username as employer_username FROM vacancies v JOIN users u ON v.employer_id = u.id WHERE v.status = ? ORDER BY v.creation_timestamp ASC LIMIT ? OFFSET ?", (status, limit, offset))
        vacancies = cursor.fetchall()
        return vacancies
    except sqlite3.Error as e:
        logger.error(f"Error retrieving vacancies with status {status}: {e}")
        return []
    finally:
        conn.close()
