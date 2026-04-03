use reqwest::Client;
use crate::models::webhook::{WebhookPayload, YookassaWebhook, MaxWebhook};
use crate::services::queue::QueueService;

#[derive(Clone)]
pub struct WebhookProcessor {
    queue: QueueService,
    http_client: Client,
    fastapi_url: String,
}

impl WebhookProcessor {
    pub fn new(redis_url: &str, fastapi_url: &str) -> Self {
        Self {
            queue: QueueService::new(redis_url),
            http_client: Client::new(),
            fastapi_url: fastapi_url.to_string(),
        }
    }

    pub async fn process_yookassa(&self, payload: &YookassaWebhook) -> Result<(), anyhow::Error> {
        println!("💰 ЮKassa: event={}", payload.event);

        if payload.event == "payment.succeeded" {
            let url = format!("{}/api/v1/webhooks/yookassa", self.fastapi_url);
            let response = self.http_client
                .post(&url)
                .json(payload)
                .send()
                .await?;

            if response.status().is_success() {
                println!("✅ Платёж обработан");
            }
        }

        Ok(())
    }

    pub async fn process_max(&self, payload: &MaxWebhook) -> Result<(), anyhow::Error> {
        println!("📨 MAX: сообщение от @{}", payload.username);

        let url = format!("{}/api/v1/webhooks/max", self.fastapi_url);
        let response = self.http_client
            .post(&url)
            .json(payload)
            .send()
            .await?;

        if response.status().is_success() {
            println!("✅ Сообщение обработано");
        }

        Ok(())
    }

    pub async fn start_background_processor(&self) {
        let processor = self.clone();
        tokio::spawn(async move {
            loop {
                if let Ok(Some(payload)) = processor.queue.pop().await {
                    println!("📦 Обработка из очереди: {:?}", payload.source);

                    match payload.source.as_str() {
                        "yookassa" => {
                            if let Ok(data) = serde_json::from_value(payload.data) {
                                let _ = processor.process_yookassa(&data).await;
                            }
                        }
                        "max" => {
                            if let Ok(data) = serde_json::from_value(payload.data) {
                                let _ = processor.process_max(&data).await;
                            }
                        }
                        _ => {}
                    }
                }
                tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
            }
        });
    }
}