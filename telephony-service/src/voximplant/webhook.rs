use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoximplantCallWebhook {
    pub event: String,
    pub call_id: String,
    pub caller_number: String,
    pub callee_number: String,
    pub duration: Option<u64>,
    pub recording_url: Option<String>,
    pub text: Option<String>,
    pub is_final: Option<bool>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoximplantSmsWebhook {
    pub message_id: String,
    pub from: String,
    pub to: String,
    pub text: String,
    pub timestamp: String,
}

pub async fn handle_call_webhook(
    _pool: &SqlitePool,
    payload: &VoximplantCallWebhook,
) -> Result<(), anyhow::Error> {
    println!("📞 Обработка звонка: call_id={}, from={}, to={}, duration={:?}",
             payload.call_id,
             payload.caller_number,
             payload.callee_number,
             payload.duration
    );

    // TODO: найти номер в БД, найти клиента, сохранить запись о звонке
    // Пока просто логируем

    Ok(())
}

pub async fn handle_sms_webhook(
    _pool: &SqlitePool,
    payload: &VoximplantSmsWebhook,
) -> Result<(), anyhow::Error> {
    println!("💬 Обработка SMS: message_id={}, from={}, to={}, text={}",
             payload.message_id,
             payload.from,
             payload.to,
             &payload.text[..payload.text.len().min(50)]
    );

    // TODO: сохранить SMS в БД
    // TODO: отправить уведомление клиенту
    // Пока просто логируем

    Ok(())
}