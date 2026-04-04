use serde::Deserialize;

#[derive(Debug, Clone, Deserialize)]
pub struct Config {
    pub server_host: String,
    pub server_port: u16,

    // Voximplant
    pub voximplant_account_id: String,
    pub voximplant_api_key: String,
    pub voximplant_api_secret: String,
    pub voximplant_webhook_secret: String,

    // База данных
    pub database_url: String,

    // FastAPI
    pub fastapi_url: String,

    // Билдинг
    pub voice_price_per_minute: f64,
    pub sms_price: f64,
}

impl Config {
    pub fn from_env() -> Self {
        dotenv::dotenv().ok();

        Self {
            server_host: std::env::var("TELEPHONY_HOST").unwrap_or_else(|_| "0.0.0.0".to_string()),
            server_port: std::env::var("TELEPHONY_PORT")
                .unwrap_or_else(|_| "8003".to_string())
                .parse()
                .unwrap_or(8003),

            voximplant_account_id: std::env::var("VOXIMPLANT_ACCOUNT_ID").expect("VOXIMPLANT_ACCOUNT_ID not set"),
            voximplant_api_key: std::env::var("VOXIMPLANT_API_KEY").expect("VOXIMPLANT_API_KEY not set"),
            voximplant_api_secret: std::env::var("VOXIMPLANT_API_SECRET").expect("VOXIMPLANT_API_SECRET not set"),
            voximplant_webhook_secret: std::env::var("VOXIMPLANT_WEBHOOK_SECRET").unwrap_or_default(),

            database_url: std::env::var("DATABASE_URL").expect("DATABASE_URL not set"),
            fastapi_url: std::env::var("FASTAPI_URL").unwrap_or_else(|_| "http://fastapi:8001".to_string()),

            voice_price_per_minute: std::env::var("VOICE_PRICE_PER_MINUTE")
                .unwrap_or_else(|_| "0.01".to_string())
                .parse()
                .unwrap_or(0.01),
            sms_price: std::env::var("SMS_PRICE")
                .unwrap_or_else(|_| "0.005".to_string())
                .parse()
                .unwrap_or(0.005),
        }
    }
}