use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use sqlx::FromRow;
use uuid::Uuid;


#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PhoneNumberStatus {
    Active,
    Suspended,
    Pending,
}

// Реализуем преобразование для SQLx
impl sqlx::Type<sqlx::Sqlite> for PhoneNumberStatus {
    fn type_info() -> sqlx::sqlite::SqliteTypeInfo {
        <String as sqlx::Type<sqlx::Sqlite>>::type_info()
    }
}

impl<'r> sqlx::Decode<'r, sqlx::Sqlite> for PhoneNumberStatus {
    fn decode(value: sqlx::sqlite::SqliteValueRef<'r>) -> Result<Self, Box<dyn std::error::Error + 'static + Send + Sync>> {
        let status = <String as sqlx::Decode<sqlx::Sqlite>>::decode(value)?;
        match status.as_str() {
            "Active" => Ok(PhoneNumberStatus::Active),
            "Suspended" => Ok(PhoneNumberStatus::Suspended),
            "Pending" => Ok(PhoneNumberStatus::Pending),
            _ => Ok(PhoneNumberStatus::Pending),
        }
    }
}

impl sqlx::Encode<'_, sqlx::Sqlite> for PhoneNumberStatus {
    fn encode_by_ref(&self, buf: &mut sqlx::sqlite::SqliteArgumentBuffer<'_>) -> sqlx::encode::IsNull {
        let s = match self {
            PhoneNumberStatus::Active => "Active",
            PhoneNumberStatus::Suspended => "Suspended",
            PhoneNumberStatus::Pending => "Pending",
        };
        <String as sqlx::Encode<sqlx::Sqlite>>::encode(s.to_string(), buf)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct PhoneNumber {
    pub id: Uuid,
    pub number: String,
    pub country: String,
    pub city: String,
    pub status: PhoneNumberStatus,
    pub client_id: Option<Uuid>,
    pub purchased_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub monthly_price: f64,
}


#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub enum PhoneNumberStatus {
    Active,
    Suspended,
    Pending,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct PhoneNumber {
    pub id: Uuid,
    pub number: String,                    // +7 XXX XXX-XX-XX
    pub country: String,                  // RU
    pub city: String,                     // Moscow
    pub status: PhoneNumberStatus,
    pub client_id: Option<Uuid>,          // Кому принадлежит
    pub purchased_at: DateTime<Utc>,
    pub expires_at: DateTime<Utc>,
    pub monthly_price: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct TelephonyClient {
    pub id: Uuid,
    pub name: String,
    pub company: String,
    pub email: String,
    pub phone: String,
    pub balance: f64,                     // Баланс в рублях
    pub is_active: bool,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct CallRecord {
    pub id: Uuid,
    pub call_id: String,                  // ID из Voximplant
    pub phone_number_id: Uuid,            // Какой номер использовался
    pub client_id: Uuid,                  // Клиент
    pub direction: String,                // incoming, outgoing
    pub caller_number: String,
    pub callee_number: String,
    pub duration: i32,                    // секунды
    pub cost: f64,                        // стоимость
    pub recording_url: Option<String>,
    pub transcript: Option<String>,       // расшифровка
    pub status: String,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize, FromRow)]
pub struct SmsRecord {
    pub id: Uuid,
    pub message_id: String,
    pub phone_number_id: Uuid,
    pub client_id: Uuid,
    pub direction: String,                // incoming, outgoing
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