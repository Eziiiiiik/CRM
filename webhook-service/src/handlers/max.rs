use axum::{Json, extract::State};
use crate::services::processor::WebhookProcessor;
use crate::models::webhook::{MaxWebhook, WebhookResponse};

pub async fn handle_max(
    State(processor): State<WebhookProcessor>,
    Json(payload): Json<MaxWebhook>,
) -> Json<WebhookResponse> {
    println!("📦 MAX webhook получен от @{}", payload.username);

    let processor_clone = processor.clone();
    tokio::spawn(async move {
        let _ = processor_clone.process_max(&payload).await;
    });

    Json(WebhookResponse {
        status: "ok".to_string(),
        message: "Webhook received".to_string(),
    })
}