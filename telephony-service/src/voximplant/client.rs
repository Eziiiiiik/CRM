use reqwest::Client;
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
        // Логируем запрос
        println!("📞 Покупка номера: страна={}, город={:?}", country, city);

        // TODO: реализовать запрос к Voximplant API
        // Пока возвращаем тестовый номер
        use rand::Rng;
        let mut rng = rand::thread_rng();
        let number = format!("+7{}", rng.gen_range(9000000000..9999999999u64));

        println!("✅ Куплен номер: {}", number);

        Ok(number)
    }
}