use futures_util::{SinkExt, StreamExt};
use log::{info, error};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{broadcast, Mutex};
use tokio_tungstenite::{accept_async, tungstenite::Message};

type Clients = Arc<Mutex<HashMap<String, tokio::sync::mpsc::UnboundedSender<Message>>>>;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    env_logger::init();
    info!("💬 Чат-сервер запускается на 127.0.0.1:3000");

    let listener = TcpListener::bind("127.0.0.1:3000").await?;
    let (tx, _) = broadcast::channel(100);
    let clients: Clients = Arc::new(Mutex::new(HashMap::new()));

    while let Ok((stream, addr)) = listener.accept().await {
        let tx = tx.clone();
        let clients = clients.clone();

        tokio::spawn(async move {
            if let Err(e) = handle_connection(stream, addr, tx, clients).await {
                error!("Ошибка: {}", e);
            }
        });
    }

    Ok(())
}

async fn handle_connection(
    stream: TcpStream,
    addr: std::net::SocketAddr,
    tx: broadcast::Sender<String>,
    clients: Clients,
) -> Result<(), Box<dyn std::error::Error>> {
    info!("📡 Новое соединение: {}", addr);

    let ws_stream = accept_async(stream).await?;
    let (mut ws_sender, mut ws_receiver) = ws_stream.split();

    let (client_sender, client_receiver) = tokio::sync::mpsc::unbounded_channel();

    {
        let mut clients_lock = clients.lock().await;
        clients_lock.insert(addr.to_string(), client_sender);
    }

    let mut rx = tx.subscribe();

    let send_task = tokio::spawn(async move {
        while let Ok(msg) = rx.recv().await {
            if ws_sender.send(Message::Text(msg)).await.is_err() {
                break;
            }
        }
    });

    let receive_task = tokio::spawn(async move {
        while let Some(msg) = ws_receiver.next().await {
            match msg {
                Ok(Message::Text(text)) => {
                    info!("Сообщение от {}: {}", addr, text);
                    let broadcast_msg = format!("{}: {}", addr, text);
                    let _ = tx.send(broadcast_msg);
                }
                Ok(Message::Close(_)) => break,
                Err(e) => {
                    error!("Ошибка: {}", e);
                    break;
                }
                _ => {}
            }
        }
    });

    tokio::select! {
        _ = send_task => {},
        _ = receive_task => {},
    }

    {
        let mut clients_lock = clients.lock().await;
        clients_lock.remove(&addr.to_string());
    }

    info!("👋 Отключился: {}", addr);
    Ok(())
}