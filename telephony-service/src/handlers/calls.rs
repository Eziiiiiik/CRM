// src/handlers/calls.rs
use axum::{extract::{State, Json}, http::StatusCode};
use sqlx::SqlitePool;
use std::sync::Arc;
use uuid::Uuid;
use chrono::Utc;

use crate::models::{MakeCallRequest, CallRecord, CallStatus};
use crate::voximplant::VoximplantClient;

pub async fn make_call(
    State(pool): State<SqlitePool>,
    State(vox_client): State<Arc<VoximplantClient>>,
    Json(req): Json<MakeCallRequest>,
) -> Result<Json<CallRecord>, (StatusCode, String)> {

    // Проверяем, что номер принадлежит клиенту
    let phone_row = sqlx::query(
        "SELECT number FROM phone_numbers WHERE id = ? AND client_id = ?",
    )
        .bind(req.from_number_id.to_string())
        .bind(req.client_id.to_string())
        .fetch_optional(&pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("DB error: {}", e)))?;

    let from_number = match phone_row {
        Some(row) => row.get::<String, _>("number"),
        None => return Err((StatusCode::FORBIDDEN, "Number not found or not owned".to_string())),
    };

    // Делаем звонок через Voximplant
    let call_id = vox_client
        .make_call(&from_number, &req.to_number, req.scenario.as_deref())
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("Voximplant error: {}", e)))?;

    let id = Uuid::new_v4();
    let now = Utc::now();

    let record = CallRecord {
        id,
        call_id: call_id.clone(),
        phone_number_id: req.from_number_id,
        client_id: Some(req.client_id),
        direction: "outgoing".to_string(),
        caller_number: from_number,
        callee_number: req.to_number.clone(),
        duration: 0,
        cost: 0.0,
        status: CallStatus::Ringing,
        created_at: now,
    };

    let status_str = match record.status {
        CallStatus::Ringing => "ringing",
        CallStatus::Completed => "completed",
        CallStatus::Failed => "failed",
        CallStatus::Busy => "busy",
    };

    let client_id_db: Option<String> = record.client_id.clone().map(|id| id.to_string());

    sqlx::query(
        r#"
        INSERT INTO call_records
            (id, call_id, phone_number_id, client_id, direction,
             caller_number, callee_number, duration, cost, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
        .bind(record.id.to_string())
        .bind(&record.call_id)
        .bind(record.phone_number_id.to_string())
        .bind(client_id_db)
        .bind(&record.direction)
        .bind(&record.caller_number)
        .bind(&record.callee_number)
        .bind(record.duration)
        .bind(record.cost)
        .bind(status_str)
        .bind(record.created_at.to_rfc3339())
        .execute(&pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("DB error: {}", e)))?;

    Ok(Json(record))
}