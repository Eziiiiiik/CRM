// src/handlers/webhooks.rs
use axum::{extract::{State, Json}, http::StatusCode, response::IntoResponse};
use sqlx::SqlitePool;
use chrono::Utc;
use uuid::Uuid;

use crate::models::CallStatus;

#[derive(Debug, serde::Deserialize)]
pub struct VoximplantWebhook {
    pub call_id: String,
    pub caller_number: String,
    pub callee_number: String,
    pub event: String,
    pub duration: Option<u32>,
    pub recording_url: Option<String>,
}

pub async fn handle_voximplant_webhook(
    State(pool): State<SqlitePool>,
    Json(payload): Json<VoximplantWebhook>,
) -> impl IntoResponse {

    tracing::info!("📞 Получен вебхук: {:?}", payload);

    match payload.event.as_str() {
        "call_started" => {
            tracing::info!("🔔 Входящий звонок от {} на {}", payload.caller_number, payload.callee_number);

            let phone = sqlx::query(
                "SELECT id, client_id FROM phone_numbers WHERE number = ?",
            )
                .bind(&payload.callee_number)
                .fetch_optional(&pool)
                .await
                .ok()
                .flatten();

            if let Some(phone) = phone {
                let now = Utc::now();
                let phone_id: String = phone.get("id");
                let client_id: Option<String> = phone.get("client_id");

                let _ = sqlx::query(
                    r#"
                    INSERT INTO call_records
                        (id, call_id, phone_number_id, client_id, direction,
                         caller_number, callee_number, duration, cost, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    "#,
                )
                    .bind(Uuid::new_v4().to_string())
                    .bind(&payload.call_id)
                    .bind(phone_id)
                    .bind(client_id)
                    .bind("incoming")
                    .bind(&payload.caller_number)
                    .bind(&payload.callee_number)
                    .bind(0i32)
                    .bind(0.0)
                    .bind("ringing")
                    .bind(now.to_rfc3339())
                    .execute(&pool)
                    .await;

                tracing::info!("✅ Входящий звонок сохранён в БД");
            } else {
                tracing::warn!("⚠️ Номер {} не найден в БД", payload.callee_number);
            }
        }
        "call_finished" => {
            tracing::info!("🏁 Звонок завершён, длительность: {:?} сек", payload.duration);
            let _ = sqlx::query(
                "UPDATE call_records SET duration = ?, status = 'completed' WHERE call_id = ?",
            )
                .bind(payload.duration.unwrap_or(0) as i32)
                .bind(&payload.call_id)
                .execute(&pool)
                .await;
        }
        _ => {
            tracing::debug!("❓ Неизвестное событие: {}", payload.event);
        }
    }

    (StatusCode::OK, "OK")
}