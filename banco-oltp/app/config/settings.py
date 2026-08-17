import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "sim"}


@dataclass(frozen=True)
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: str = os.getenv("POSTGRES_PORT", "5434")
    postgres_db: str = os.getenv("POSTGRES_DB", "estoque_banco")
    postgres_user: str = os.getenv("POSTGRES_USER", "estoque_banco_user")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "estoque_banco_pwd")

    kafka_bootstrap_servers: str = os.getenv(
        "KAFKA_BOOTSTRAP_SERVERS", "localhost:19090"
    )
    kafka_topic_reabastecimento: str = os.getenv(
        "KAFKA_TOPIC_REABASTECIMENTO", "reabastecimento"
    )
    enable_replenishment_consumer: bool = _bool_env(
        "ENABLE_REPLENISHMENT_CONSUMER", True
    )
    kafka_reconnect_seconds: int = int(
        os.getenv("KAFKA_RECONNECT_SECONDS", "5")
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
