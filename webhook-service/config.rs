use serde::Deserialize;
use std::env;

#[derive(Debug, Clone)]
pub struct Config {
    pub server_host: String,
    pub server_port: u16,
    pub redis_url: String,
    pub fastapi_url: String,

    // Секретные ключи
    pub yookassa_secret: String,
    pub max_secret: String,
}

impl Config {
    pub fn from_env() -> Self {
        Self {
            server_host: env::var("WEBHOOK_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            server_port: env::var("WEBHOOK_PORT")
                .unwrap_or_else(|_| "8002".to_string())
                .parse()
                .unwrap_or(8002),
            redis_url: env::var("REDIS_URL").unwrap_or_else(|_| "redis://redis:6379".to_string()),
            fastapi_url: env::var("FASTAPI_URL").unwrap_or_else(|_| "http://fastapi:8001".to_string()),
            yookassa_secret: env::var("YOOKASSA_WEBHOOK_SECRET").unwrap_or_default(),
            max_secret: env::var("MAX_WEBHOOK_SECRET").unwrap_or_default(),
        }
    }
}