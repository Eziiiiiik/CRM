use serde::{Deserialize, Serialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebhookPayload {
    pub id: String,
    pub source: String,
    pub event_type: String,
    pub data: serde_json::Value,
    pub received_at: DateTime<Utc>,
    pub processed: bool,
}

// ========== ЮKassa ==========

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YookassaWebhook {
    pub event: String,
    pub object: YookassaPayment,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YookassaPayment {
    pub id: String,
    pub status: String,
    pub amount: YookassaAmount,
    pub metadata: YookassaMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YookassaAmount {
    pub value: String,
    pub currency: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct YookassaMetadata {
    pub deal_id: i32,
}

// ========== MAX ==========

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MaxWebhook {
    pub message_id: String,
    pub chat_id: String,
    pub text: String,
    pub username: String,
    pub first_name: String,
    pub user_id: String,
}

// ========== Ответы ==========

#[derive(Debug, Serialize)]
pub struct WebhookResponse {
    pub status: String,
    pub message: String,
}