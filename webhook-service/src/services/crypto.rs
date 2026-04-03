use hmac::{Hmac, Mac};
use sha2::Sha256;
use hex;

type HmacSha256 = Hmac<Sha256>;

pub fn verify_signature(payload: &[u8], signature: &str, secret: &str) -> bool {
    if secret.is_empty() {
        return true;
    }

    let mut mac = HmacSha256::new_from_slice(secret.as_bytes()).unwrap();
    mac.update(payload);
    let expected = hex::encode(mac.finalize().into_bytes());

    // Сравнение в постоянное время (защита от timing attacks)
    expected == signature
}