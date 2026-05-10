// src/config.rs
use serde::Deserialize;

#[derive(Clone, Deserialize)]
pub struct Config {
    pub server_host: String,
    pub server_port: u16,
    pub database_url: String,

    pub voximplant_account_id: String,
    pub voximplant_api_key: String,

    pub secret_key: String,
    pub fastapi_url: Option<String>,

    // Billing prices
    #[serde(default = "default_voice_price")]
    pub voice_price_per_minute: f64,

    #[serde(default = "default_sms_price")]
    pub sms_price: f64,
}

fn default_voice_price() -> f64 { 0.01 }
fn default_sms_price() -> f64 { 0.005 }

impl Config {
    pub fn from_env() -> Self {
        dotenvy::dotenv().ok();

        Config {
            server_host: std::env::var("TELEPHONY_HOST")
                .unwrap_or_else(|_| "0.0.0.0".to_string()),
            server_port: std::env::var("TELEPHONY_PORT")
                .unwrap_or_else(|_| "8003".to_string())
                .parse()
                .unwrap_or(8003),
            database_url: std::env::var("TELEPHONY_DATABASE_URL")
                .unwrap_or_else(|_| "sqlite:./telephony.db".to_string()),
            voximplant_account_id: std::env::var("VOXIMPLANT_ACCOUNT_ID")
                .expect("VOXIMPLANT_ACCOUNT_ID must be set"),
            voximplant_api_key: std::env::var("VOXIMPLANT_API_KEY")
                .expect("VOXIMPLANT_API_KEY must be set"),
            secret_key: std::env::var("SECRET_KEY")
                .expect("SECRET_KEY must be set"),
            fastapi_url: std::env::var("FASTAPI_URL").ok(),
            voice_price_per_minute: std::env::var("VOICE_PRICE_PER_MINUTE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or_else(default_voice_price),
            sms_price: std::env::var("SMS_PRICE")
                .ok()
                .and_then(|v| v.parse().ok())
                .unwrap_or_else(default_sms_price),
        }
    }
}