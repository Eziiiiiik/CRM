use axum::{Json, extract::State};
use crate::models::CallRecord;
use sqlx::SqlitePool;
use uuid::Uuid;
use chrono::Utc;

#[derive(Debug, serde::Deserialize)]
pub struct VoximplantWebhook {
    pub call_id: String,
    pub caller_number: String,
    pub callee_number: String,
    pub event: String,
    pub duration: Option<u32>,
}

pub async fn handle_voximplant_webhook(
    State(pool): State<SqlitePool>,
    Json(payload): Json<VoximplantWebhook>,
) -> &'static str {
    println!("📞 Входящий вебхук: {:?}", payload);

    if payload.event == "call_started" {
        // Ищем номер в БД
        let phone = sqlx::query!(
            "SELECT id, client_id FROM phone_numbers WHERE number = ?",
            payload.callee_number
        )
            .fetch_optional(&pool)
            .await
            .unwrap();

        if let Some(phone) = phone {
            // Сохраняем входящий звонок
            let _ = sqlx::query!(
                r#"
                INSERT INTO call_records (id, call_id, phone_number_id, client_id, direction,
                                           caller_number, callee_number, duration, cost, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                "#,
                Uuid::new_v4().to_string(),
                payload.call_id,
                phone.id,
                phone.client_id,
                "incoming",
                payload.caller_number,
                payload.callee_number,
                0,
                0.0,
                "ringing",
                Utc::now().to_rfc3339()
            )
                .execute(&pool)
                .await;
        }
    }

    "OK"
}