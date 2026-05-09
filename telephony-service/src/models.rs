use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, sqlx::Type)]
#[sqlx(type_name = "TEXT")]
pub enum PhoneNumberStatus {
    Active,
    Suspended,
    Pending,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct PhoneNumber {
    pub id: Uuid,
    pub number: String,
    pub country: String,
    pub city: Option<String>,
    pub status: PhoneNumberStatus,
    pub client_id: Option<Uuid>,
    pub purchased_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub monthly_price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct TelephonyClient {
    pub id: Uuid,
    pub name: String,
    pub company: Option<String>,
    pub email: String,
    pub phone: String,
    pub balance: f64,
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct CallRecord {
    pub id: Uuid,
    pub call_id: String,
    pub phone_number_id: Uuid,
    pub client_id: Uuid,
    pub direction: String,
    pub caller_number: String,
    pub callee_number: String,
    pub duration: i32,
    pub cost: f64,
    pub recording_url: Option<String>,
    pub transcript: Option<String>,
    pub status: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct SmsRecord {
    pub id: Uuid,
    pub message_id: String,
    pub phone_number_id: Uuid,
    pub client_id: Uuid,
    pub direction: String,
    pub from_number: String,
    pub to_number: String,
    pub text: String,
    pub cost: f64,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateNumberRequest {
    pub country: String,
    pub city: Option<String>,
    pub client_id: Option<Uuid>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TopUpRequest {
    pub client_id: Uuid,
    pub amount: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MakeCallRequest {
    pub from_number_id: Uuid,
    pub to_number: String,
    pub client_id: Uuid,
}