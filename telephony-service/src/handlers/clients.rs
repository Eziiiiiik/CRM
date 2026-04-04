use axum::{Json, extract::State};
use crate::models::{TelephonyClient, TopUpRequest};
use sqlx::SqlitePool;
use uuid::Uuid;
use chrono::Utc;

pub async fn create_client(
    State(pool): State<SqlitePool>,
    Json(client_data): Json<TelephonyClient>,
) -> Result<Json<TelephonyClient>, axum::http::StatusCode> {
    let id = Uuid::new_v4();
    let now = Utc::now();

    let client = TelephonyClient {
        id,
        name: client_data.name,
        company: client_data.company,
        email: client_data.email,
        phone: client_data.phone,
        balance: 0.0,
        is_active: true,
        created_at: now,
    };

    sqlx::query(
        r#"
        INSERT INTO telephony_clients (id, name, company, email, phone, balance, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        "#
    )
        .bind(client.id.to_string())
        .bind(&client.name)
        .bind(&client.company)
        .bind(&client.email)
        .bind(&client.phone)
        .bind(client.balance)
        .bind(client.is_active)
        .bind(client.created_at.to_rfc3339())
        .execute(&pool)
        .await
        .map_err(|_| axum::http::StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(client))
}

pub async fn top_up_balance(
    State(pool): State<SqlitePool>,
    Json(req): Json<TopUpRequest>,
) -> Result<String, axum::http::StatusCode> {
    sqlx::query(
        r#"
        UPDATE telephony_clients
        SET balance = balance + ?
        WHERE id = ?
        "#
    )
        .bind(req.amount)
        .bind(req.client_id.to_string())
        .execute(&pool)
        .await
        .map_err(|_| axum::http::StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok("Balance topped up".to_string())
}