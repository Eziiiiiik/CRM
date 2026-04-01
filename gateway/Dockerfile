FROM rust:1.85-slim as builder

WORKDIR /app
COPY . .
RUN cargo build --release

FROM debian:bookworm-slim
COPY --from=builder /app/target/release/gateway /usr/local/bin/gateway
EXPOSE 5900
CMD ["gateway"]