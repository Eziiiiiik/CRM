// src/handlers/numbers.rs
use axum::{extract::{State, Json}, http::StatusCode};
use sqlx::SqlitePool;
use std::sync::Arc;
use uuid::Uuid;
use chrono::Utc;

use crate::models::{CreateNumberRequest, PhoneNumber, PhoneNumberStatus};
use crate::voximplant::VoximplantClient;

pub async fn purchase_number(
    State(pool): State<SqlitePool>,
    State(vox_client): State<Arc<VoximplantClient>>,
    Json(req): Json<CreateNumberRequest>,
) -> Result<Json<PhoneNumber>, (StatusCode, String)> {

    let number = vox_client
        .purchase_number(&req.country, req.city.as_deref())
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("Voximplant error: {}", e)))?;

    let id = Uuid::new_v4();
    let now = Utc::now();
    let expires_at = now + chrono::Duration::days(30);

    let phone = PhoneNumber {
        id,
        number: number.clone(),
        country: req.country.clone(),
        city: req.city.clone(),
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

    let client_id_db: Option<String> = phone.client_id.map(|id| id.to_string());
    let city_db: Option<String> = phone.city.clone();

    sqlx::query(
        r#"
        INSERT INTO phone_numbers
            (id, number, country, city, status, client_id, purchased_at, expires_at, monthly_price)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        "#,
    )
        .bind(phone.id.to_string())
        .bind(&phone.number)
        .bind(&phone.country)
        .bind(city_db)
        .bind(status_str)
        .bind(client_id_db)
        .bind(phone.purchased_at.to_rfc3339())
        .bind(phone.expires_at.to_rfc3339())
        .bind(phone.monthly_price)
        .execute(&pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("DB error: {}", e)))?;

    Ok(Json(phone))
}

pub async fn get_numbers(
    State(pool): State<SqlitePool>,
) -> Result<Json<Vec<PhoneNumber>>, (StatusCode, String)> {

    let rows = sqlx::query(
        r#"
        SELECT id, number, country, city, status, client_id, purchased_at, expires_at, monthly_price
        FROM phone_numbers
        ORDER BY purchased_at DESC
        "#,
    )
        .fetch_all(&pool)
        .await
        .map_err(|e| (StatusCode::INTERNAL_SERVER_ERROR, format!("DB error: {}", e)))?;

    let numbers: Result<Vec<PhoneNumber>, (StatusCode, String)> = rows.into_iter().map(|row| {
        let id = Uuid::parse_str(row.get::<String, _>("id"))
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Invalid UUID format".to_string()))?;

        let client_id: Option<String> = row.get::<Option<String>, _>("client_id");
        let client_id = client_id.and_then(|id| Uuid::parse_str(&id).ok());

        let status_str: String = row.get("status");
        let status = match status_str.as_str() {
            "Active" => PhoneNumberStatus::Active,
            "Suspended" => PhoneNumberStatus::Suspended,
            _ => PhoneNumberStatus::Pending,
        };

        let purchased_at_str: String = row.get("purchased_at");
        let expires_at_str: String = row.get("expires_at");

        let purchased_at = chrono::DateTime::parse_from_rfc3339(&purchased_at_str)
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Invalid date format".to_string()))?
            .with_timezone(&Utc);
        let expires_at = chrono::DateTime::parse_from_rfc3339(&expires_at_str)
            .map_err(|_| (StatusCode::INTERNAL_SERVER_ERROR, "Invalid date format".to_string()))?
            .with_timezone(&Utc);

        Ok(PhoneNumber {
            id,
            number: row.get("number"),
            country: row.get("country"),
            city: row.get("city"),
            status,
            client_id,
            purchased_at,
            expires_at,
            monthly_price: row.get("monthly_price"),
        })
    }).collect();

    numbers.map(Json)
}