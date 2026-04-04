use axum::{Json, extract::State, http::StatusCode};
use crate::models::{CreateNumberRequest, PhoneNumber, PhoneNumberStatus};
use crate::voximplant::VoximplantClient;
use sqlx::{SqlitePool, Row};
use uuid::Uuid;
use chrono::{Utc, Duration};
use std::sync::Arc;

pub async fn purchase_number(
    State((pool, voximplant)): State<(SqlitePool, VoximplantClient)>,
    Json(req): Json<CreateNumberRequest>,
) -> Result<Json<PhoneNumber>, StatusCode> {
    // Покупаем номер через Voximplant
    let number = voximplant
        .purchase_number(&req.country, req.city.as_deref())
        .await
        .map_err(|e| {
            eprintln!("Voximplant error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    // Сохраняем в БД
    let id = Uuid::new_v4();
    let now = Utc::now();
    let expires_at = now + Duration::days(30);

    let phone = PhoneNumber {
        id,
        number: number.clone(),
        country: req.country,
        city: req.city.clone().unwrap_or_default(),
        status: PhoneNumberStatus::Active,
        client_id: req.client_id,
        purchased_at: now,
        expires_at,
        monthly_price: 0.01,
    };

    let status_str = match phone.status {
        PhoneNumberStatus::Active => "Active",
        PhoneNumberStatus::Suspended => "Suspended",
        PhoneNumberStatus::Pending => "Pending",
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
        .bind(status_str)
        .bind(phone.client_id.map(|id| id.to_string()))
        .bind(phone.purchased_at.to_rfc3339())
        .bind(phone.expires_at.to_rfc3339())
        .bind(phone.monthly_price)
        .execute(&pool)
        .await
        .map_err(|e| {
            eprintln!("DB error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    Ok(Json(phone))
}

pub async fn get_numbers(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<PhoneNumber>>, StatusCode> {
    let rows = sqlx::query(
        r#"
        SELECT id, number, country, city, status, client_id, purchased_at, expires_at, monthly_price
        FROM phone_numbers
        ORDER BY purchased_at DESC
        "#
    )
        .fetch_all(&pool)
        .await
        .map_err(|e| {
            eprintln!("DB error: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

    let mut numbers = Vec::new();

    for row in rows {
        let id_str: &str = row.try_get("id").map_err(|e| {
            eprintln!("Error parsing id: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let id = Uuid::parse_str(id_str).map_err(|e| {
            eprintln!("Error parsing UUID: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let number: String = row.try_get("number").map_err(|e| {
            eprintln!("Error parsing number: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let country: String = row.try_get("country").map_err(|e| {
            eprintln!("Error parsing country: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let city: String = row.try_get("city").unwrap_or_default();

        let status_str: &str = row.try_get("status").unwrap_or("Pending");
        let status = match status_str {
            "Active" => PhoneNumberStatus::Active,
            "Suspended" => PhoneNumberStatus::Suspended,
            _ => PhoneNumberStatus::Pending,
        };

        let client_id_str: Option<String> = row.try_get("client_id").ok();
        let client_id = client_id_str.and_then(|s| Uuid::parse_str(&s).ok());

        let purchased_at_str: &str = row.try_get("purchased_at").map_err(|e| {
            eprintln!("Error parsing purchased_at: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let purchased_at = chrono::DateTime::parse_from_rfc3339(purchased_at_str)
            .map_err(|e| {
                eprintln!("Error parsing purchased_at date: {}", e);
                StatusCode::INTERNAL_SERVER_ERROR
            })?
            .with_timezone(&chrono::Utc);

        let expires_at_str: &str = row.try_get("expires_at").map_err(|e| {
            eprintln!("Error parsing expires_at: {}", e);
            StatusCode::INTERNAL_SERVER_ERROR
        })?;

        let expires_at = chrono::DateTime::parse_from_rfc3339(expires_at_str)
            .map_err(|e| {
                eprintln!("Error parsing expires_at date: {}", e);
                StatusCode::INTERNAL_SERVER_ERROR
            })?
            .with_timezone(&chrono::Utc);

        let monthly_price: f64 = row.try_get("monthly_price").unwrap_or(0.0);

        numbers.push(PhoneNumber {
            id,
            number,
            country,
            city,
            status,
            client_id,
            purchased_at,
            expires_at,
            monthly_price,
        });
    }

    Ok(Json(numbers))
}