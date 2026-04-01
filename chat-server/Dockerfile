FROM rust:1.85-slim as builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/chat-server /usr/local/bin/chat-server
EXPOSE 3000
CMD ["chat-server"]