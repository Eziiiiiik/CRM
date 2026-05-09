use axum::{Json, extract::State, http::StatusCode};
use crate::models::{MakeCallRequest, CallRecord};
use crate::voximplant::VoximplantClient;
use sqlx::SqlitePool;
use uuid::Uuid;
use chrono::Utc;

pub async fn make_call(
    State((pool, voximplant)): State<(SqlitePool, VoximplantClient)>,
    Json(req): Json<MakeCallRequest>,
) -> Result<Json<CallRecord>, StatusCode> {
    // Получаем номер телефона из БД
    let phone = sqlx::query_as::<_, (String,)>(
        "SELECT number FROM phone_numbers WHERE id = ? AND client_id = ?"
    )
        .bind(req.from_number_id.to_string())
        .bind(req.client_id.to_string())
        .fetch_one(&pool)
        .await
        .map_err(|_| StatusCode::NOT_FOUND)?;

    // Совершаем звонок через Voximplant
    let call_id = voximplant.make_call(&phone.0, &req.to_number)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Сохраняем запись о звонке
    let record = CallRecord {
        id: Uuid::new_v4(),
        call_id,
        phone_number_id: req.from_number_id,
        client_id: req.client_id,
        direction: "outgoing".to_string(),
        caller_number: phone.0,
        callee_number: req.to_number,
        duration: 0,
        cost: 0.0,
        recording_url: None,
        transcript: None,
        status: "initiated".to_string(),
        created_at: Utc::now(),
    };

    sqlx::query(
        r#"
        INSERT INTO call_records (id, call_id, phone_number_id, client_id, direction, 
                                   caller_number, callee_number, duration, cost, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#
    )
        .bind(record.id.to_string())
        .bind(&record.call_id)
        .bind(record.phone_number_id.to_string())
        .bind(record.client_id.to_string())
        .bind(&record.direction)
        .bind(&record.caller_number)
        .bind(&record.callee_number)
        .bind(record.duration)
        .bind(record.cost)
        .bind(&record.status)
        .bind(record.created_at.to_rfc3339())
        .execute(&pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(record))
}