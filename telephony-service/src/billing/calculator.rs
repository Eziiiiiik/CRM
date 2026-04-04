use crate::config::Config;

pub struct BillingCalculator {
    config: Config,
}

impl BillingCalculator {
    pub fn new(config: Config) -> Self {
        Self { config }
    }

    pub fn calculate_call_cost(&self, duration_seconds: i32) -> f64 {
        let minutes = duration_seconds as f64 / 60.0;
        minutes * self.config.voice_price_per_minute
    }

    pub fn calculate_sms_cost(&self) -> f64 {
        self.config.sms_price
    }

    pub fn deduct_balance(&self, current_balance: f64, cost: f64) -> Result<f64, String> {
        if current_balance < cost {
            return Err("Insufficient balance".to_string());
        }
        Ok(current_balance - cost)
    }
}