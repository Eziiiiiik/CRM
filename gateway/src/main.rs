use hyper::service::{make_service_fn, service_fn};
use hyper::{Body, Request, Response, Server, StatusCode, Uri};
use std::convert::Infallible;
use std::net::SocketAddr;
use std::time::Instant;
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;

// Простая статистика
struct Stats {
    total_requests: u64,
    by_path: HashMap<String, u64>,
}

impl Stats {
    fn new() -> Self {
        Self {
            total_requests: 0,
            by_path: HashMap::new(),
        }
    }

    fn record(&mut self, path: &str) {
        self.total_requests += 1;
        *self.by_path.entry(path.to_string()).or_insert(0) += 1;
    }
}

type SharedStats = Arc<Mutex<Stats>>;

// Прокси-обработчик
async fn handle_request(
    req: Request<Body>,
    stats: SharedStats,
) -> Result<Response<Body>, hyper::Error> {
    let start = Instant::now();
    let path = req.uri().path().to_string();
    let method = req.method().clone();
    let headers = req.headers().clone();

    // Обновляем статистику
    {
        let mut stats_lock = stats.lock().await;
        stats_lock.record(&path);
    }

    // Адрес FastAPI — в Docker используем имя сервиса, в Windows localhost
    // Определяем по наличию переменной окружения DOCKER_ENV
    let fastapi_addr = match std::env::var("DOCKER_ENV") {
        Ok(_) => "http://fastapi:8001",
        Err(_) => {
            if cfg!(target_os = "windows") {
                "http://127.0.0.1:8001"
            } else {
                "http://host.docker.internal:8001"
            }
        }
    };

    let uri_str = format!("{}{}", fastapi_addr, path);
    let uri: Uri = match uri_str.parse() {
        Ok(u) => u,
        Err(e) => {
            eprintln!("Ошибка парсинга URI {}: {}", uri_str, e);
            let mut resp = Response::new(Body::from("Bad Request"));
            *resp.status_mut() = StatusCode::BAD_REQUEST;
            return Ok(resp);
        }
    };

    // Создаём новый запрос
    let client = hyper::Client::new();
    let mut new_req = Request::builder()
        .method(method.clone())
        .uri(uri);

    // Копируем заголовки
    for (name, value) in headers.iter() {
        new_req = new_req.header(name, value);
    }

    let new_req = match new_req.body(req.into_body()) {
        Ok(req) => req,
        Err(e) => {
            eprintln!("Ошибка создания запроса: {}", e);
            let mut resp = Response::new(Body::from("Internal Server Error"));
            *resp.status_mut() = StatusCode::INTERNAL_SERVER_ERROR;
            return Ok(resp);
        }
    };

    // Отправляем запрос
    match client.request(new_req).await {
        Ok(resp) => {
            let elapsed = start.elapsed();
            println!("{} {} - {}ms", method, path, elapsed.as_millis());
            Ok(resp)
        }
        Err(e) => {
            eprintln!("Ошибка прокси: {}", e);
            let mut resp = Response::new(Body::from("Bad Gateway"));
            *resp.status_mut() = StatusCode::BAD_GATEWAY;
            Ok(resp)
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let addr = SocketAddr::from(([0, 0, 0, 0], 5900));
    let stats: SharedStats = Arc::new(Mutex::new(Stats::new()));

    println!("🚀 Gateway запущен на http://{}", addr);
    println!("📡 Проксирует запросы на FastAPI");

    let stats_clone = stats.clone();
    let make_svc = make_service_fn(move |_conn| {
        let stats = stats_clone.clone();
        async move {
            Ok::<_, Infallible>(service_fn(move |req| {
                handle_request(req, stats.clone())
            }))
        }
    });

    let server = Server::bind(&addr).serve(make_svc);

    println!("✅ Gateway готов к работе");

    if let Err(e) = server.await {
        eprintln!("Ошибка сервера: {}", e);
    }

    // Выводим статистику при завершении
    let final_stats = stats.lock().await;
    println!("\n📊 Статистика:");
    println!("Всего запросов: {}", final_stats.total_requests);
    for (path, count) in &final_stats.by_path {
        println!("  {}: {}", path, count);
    }

    Ok(())
}