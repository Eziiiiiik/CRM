use sqlx::sqlite::SqlitePool;
use sqlx::{SqlitePool as Pool, migrate::MigrateDatabase};

pub async fn init_db(database_url: &str) -> Result<Pool, anyhow::Error> {
    if !sqlx::Sqlite::database_exists(database_url).await? {
        sqlx::Sqlite::create_database(database_url).await?;
    }

    let pool = SqlitePool::connect(database_url).await?;

    // Таблица номеров
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS phone_numbers (
            id TEXT PRIMARY KEY,
            number TEXT NOT NULL UNIQUE,
            country TEXT NOT NULL,
            city TEXT,
            status TEXT NOT NULL,
            client_id TEXT,
            purchased_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            monthly_price REAL NOT NULL
        )
        "#
    ).execute(&pool).await?;

    // Таблица клиентов
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS telephony_clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            company TEXT,
            email TEXT NOT NULL UNIQUE,
            phone TEXT NOT NULL,
            balance REAL NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        "#
    ).execute(&pool).await?;

    // Таблица звонков
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS call_records (
            id TEXT PRIMARY KEY,
            call_id TEXT NOT NULL UNIQUE,
            phone_number_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            caller_number TEXT NOT NULL,
            callee_number TEXT NOT NULL,
            duration INTEGER NOT NULL,
            cost REAL NOT NULL,
            recording_url TEXT,
            transcript TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        "#
    ).execute(&pool).await?;

    // Таблица SMS
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS sms_records (
            id TEXT PRIMARY KEY,
            message_id TEXT NOT NULL UNIQUE,
            phone_number_id TEXT NOT NULL,
            client_id TEXT NOT NULL,
            direction TEXT NOT NULL,
            from_number TEXT NOT NULL,
            to_number TEXT NOT NULL,
            text TEXT NOT NULL,
            cost REAL NOT NULL,
            created_at TEXT NOT NULL
        )
        "#
    ).execute(&pool).await?;

    Ok(pool)
}