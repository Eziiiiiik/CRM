use axum::{Json, extract::State};
use crate::services::processor::WebhookProcessor;
use crate::models::webhook::{YookassaWebhook, WebhookResponse};

pub async fn handle_yookassa(
    State(processor): State<WebhookProcessor>,
    Json(payload): Json<YookassaWebhook>,
) -> Json<WebhookResponse> {
    println!("📦 ЮKassa webhook получен");

    // Обрабатываем асинхронно
    let processor_clone = processor.clone();
    tokio::spawn(async move {
        let _ = processor_clone.process_yookassa(&payload).await;
    });

    Json(WebhookResponse {
        status: "ok".to_string(),
        message: "Webhook received".to_string(),
    })
}