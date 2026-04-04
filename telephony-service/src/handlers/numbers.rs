use axum::{Json, extract::State, http::StatusCode};
use crate::models::{CreateNumberRequest, PhoneNumber};
use crate::voximplant::VoximplantClient;
use sqlx::SqlitePool;
use uuid::Uuid;
use chrono::{Utc, Duration};

pub async fn purchase_number(
    State((pool, voximplant)): State<(SqlitePool, VoximplantClient)>,
    Json(req): Json<CreateNumberRequest>,
) -> Result<Json<PhoneNumber>, StatusCode> {
    // Покупаем номер через Voximplant
    let number = voximplant
        .purchase_number(&req.country, req.city.as_deref())
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    // Сохраняем в БД
    let id = Uuid::new_v4();
    let now = Utc::now();
    let expires_at = now + Duration::days(30);

    let phone = PhoneNumber {
        id,
        number,
        country: req.country,
        city: req.city.unwrap_or_default(),
        status: crate::models::PhoneNumberStatus::Active,
        client_id: req.client_id,
        purchased_at: now,
        expires_at,
        monthly_price: 0.01,
    };

    sqlx::query(
        r#"
        INSERT INTO phone_numbers (id, number, country, city, status, client_id, purchased_at, expires_at, monthly_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#
    )
        .bind(phone.id.to_string())
        .bind(&phone.number)
        .bind(&phone.country)
        .bind(&phone.city)
        .bind("Active")
        .bind(phone.client_id.map(|id| id.to_string()))
        .bind(phone.purchased_at.to_rfc3339())
        .bind(phone.expires_at.to_rfc3339())
        .bind(phone.monthly_price)
        .execute(&pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(phone))
}

pub async fn get_numbers(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<PhoneNumber>>, StatusCode> {
    let numbers = sqlx::query_as::<_, PhoneNumber>(
        r#"
        SELECT id, number, country, city, status, client_id, purchased_at, expires_at, monthly_price
        FROM phone_numbers
        ORDER BY purchased_at DESC
        "#
    )
        .fetch_all(&pool)
        .await
        .map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;

    Ok(Json(numbers))
}