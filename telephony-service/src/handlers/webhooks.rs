use axum::{Json, extract::State};
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
    pub recording_url: Option<String>,
}

pub async fn handle_voximplant_webhook(
    State(pool): State<SqlitePool>,
    Json(payload): Json<VoximplantWebhook>,
) -> &'static str {
    println!("📞 Получен вебхук: {:?}", payload);

    // Просто логируем и возвращаем успех (без проверок подписи)
    match payload.event.as_str() {
        "call_started" => {
            println!("🔔 Входящий звонок от {} на {}", payload.caller_number, payload.callee_number);

            // Ищем номер в БД
            let phone = sqlx::query!(
                "SELECT id, client_id FROM phone_numbers WHERE number = ?",
                payload.callee_number
            )
                .fetch_optional(&pool)
                .await
                .unwrap_or(None);

            if let Some(phone) = phone {
                // Сохраняем запись о звонке
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
        "call_finished" => {
            println!("🏁 Звонок завершён, длительность: {:?} сек", payload.duration);
            // Обновляем запись о звонке
            let _ = sqlx::query!(
                "UPDATE call_records SET duration = ?, status = 'completed' WHERE call_id = ?",
                payload.duration.unwrap_or(0) as i32,
                payload.call_id
            )
                .execute(&pool)
                .await;
        }
        _ => {
            println!("❓ Неизвестное событие: {}", payload.event);
        }
    }

    "OK"
}