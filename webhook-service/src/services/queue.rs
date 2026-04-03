use redis::{AsyncCommands, Client, RedisResult};
use serde_json;
use crate::models::webhook::WebhookPayload;

pub struct QueueService {
    client: Client,
}

impl QueueService {
    pub fn new(redis_url: &str) -> Self {
        let client = Client::open(redis_url).unwrap();
        Self { client }
    }

    pub async fn push(&self, payload: &WebhookPayload) -> RedisResult<()> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let json = serde_json::to_string(payload).unwrap();
        conn.lpush("webhook_queue", json).await?;
        Ok(())
    }

    pub async fn pop(&self) -> RedisResult<Option<WebhookPayload>> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let result: Option<String> = conn.rpop("webhook_queue", None).await?;

        match result {
            Some(json) => Ok(serde_json::from_str(&json).ok()),
            None => Ok(None),
        }
    }

    pub async fn size(&self) -> RedisResult<usize> {
        let mut conn = self.client.get_multiplexed_async_connection().await?;
        let size: usize = conn.llen("webhook_queue").await?;
        Ok(size)
    }
}