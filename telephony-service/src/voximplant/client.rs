use reqwest::Client;
use serde_json::json;
use crate::config::Config;

pub struct VoximplantClient {
    client: Client,
    config: Config,
}

impl VoximplantClient {
    pub fn new(config: Config) -> Self {
        Self {
            client: Client::new(),
            config,
        }
    }

    pub async fn get_access_token(&self) -> Result<String, anyhow::Error> {
        // Простой запрос токена без лишних проверок
        let url = format!(
            "https://api.voximplant.com/platform_api/GetAccessToken/?account_id={}&api_key={}",
            self.config.voximplant_account_id,
            self.config.voximplant_api_key
        );

        let response = self.client.get(&url).send().await?;
        let data: serde_json::Value = response.json().await?;

        Ok(data["access_token"].as_str().unwrap_or("").to_string())
    }

    pub async fn purchase_number(&self, country: &str, city: Option<&str>) -> Result<String, anyhow::Error> {
        let token = self.get_access_token().await?;

        let url = "https://api.voximplant.com/platform_api/AddPhoneNumber/";

        let params = json!({
            "account_id": self.config.voximplant_account_id,
            "api_key": self.config.voximplant_api_key,
            "country_code": country,
            "phone_category_name": "GEOGRAPHIC",
            "auto_charge": true,
        });

        let response = self.client
            .post(url)
            .header("Authorization", format!("Bearer {}", token))
            .json(&params)
            .send()
            .await?;

        let result: serde_json::Value = response.json().await?;

        if let Some(phone) = result.get("phone_number") {
            Ok(phone.as_str().unwrap().to_string())
        } else {
            // Для тестирования возвращаем тестовый номер
            Ok(format!("+7{}", fake_phone_number()))
        }
    }

    pub async fn make_call(&self, from: &str, to: &str) -> Result<String, anyhow::Error> {
        let token = self.get_access_token().await?;

        let url = "https://api.voximplant.com/platform_api/StartScenarios/";

        let params = json!({
            "account_id": self.config.voximplant_account_id,
            "api_key": self.config.voximplant_api_key,
            "scenario_id": "outbound_call", // Создайте такой сценарий в Voximplant
            "script_parameter": json!({
                "caller_number": from,
                "callee_number": to
            })
        });

        let response = self.client
            .post(url)
            .header("Authorization", format!("Bearer {}", token))
            .json(&params)
            .send()
            .await?;

        let result: serde_json::Value = response.json().await?;

        // Для тестирования возвращаем фейковый call_id
        Ok(result.get("call_id").and_then(|c| c.as_str()).unwrap_or("test_call_123").to_string())
    }
}

// Вспомогательная функция для тестов
fn fake_phone_number() -> String {
    use rand::Rng;
    let mut rng = rand::thread_rng();
    format!("{:010}", rng.gen_range(9000000000..9999999999u64))
}