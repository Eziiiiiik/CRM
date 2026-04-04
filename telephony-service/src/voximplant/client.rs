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

    pub async fn purchase_number(&self, country: &str, city: Option<&str>) -> Result<String, anyhow::Error> {
        let url = "https://api.voximplant.com/platform_api/AddPhoneNumber/";

        let mut params = vec![
            ("account_id", &self.config.voximplant_account_id),
            ("api_key", &self.config.voximplant_api_key),
            ("country_code", country),
        ];

        if let Some(city) = city {
            params.push(("phone_category_name", city));
        }

        let response = self.client
            .post(url)
            .form(&params)
            .send()
            .await?;

        let result = response.json::<serde_json::Value>().await?;
        let phone_number = result["result"]["phone_number"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Failed to purchase number"))?;

        Ok(phone_number.to_string())
    }

    pub async fn get_numbers(&self) -> Result<Vec<String>, anyhow::Error> {
        let url = "https://api.voximplant.com/platform_api/GetPhoneNumbers/";

        let params = [
            ("account_id", &self.config.voximplant_account_id),
            ("api_key", &self.config.voximplant_api_key),
        ];

        let response = self.client
            .post(url)
            .form(&params)
            .send()
            .await?;

        let result = response.json::<serde_json::Value>().await?;
        let numbers = result["result"]["numbers"]
            .as_array()
            .unwrap_or(&vec![])
            .iter()
            .filter_map(|n| n["phone_number"].as_str().map(|s| s.to_string()))
            .collect();

        Ok(numbers)
    }

    pub async fn send_sms(&self, from: &str, to: &str, text: &str) -> Result<String, anyhow::Error> {
        let url = "https://api.voximplant.com/platform_api/SendSms/";

        let params = [
            ("account_id", &self.config.voximplant_account_id),
            ("api_key", &self.config.voximplant_api_key),
            ("source", from),
            ("destination", to),
            ("sms_body", text),
        ];

        let response = self.client
            .post(url)
            .form(&params)
            .send()
            .await?;

        let result = response.json::<serde_json::Value>().await?;
        let message_id = result["result"]["message_id"]
            .as_str()
            .ok_or_else(|| anyhow::anyhow!("Failed to send SMS"))?;

        Ok(message_id.to_string())
    }
}