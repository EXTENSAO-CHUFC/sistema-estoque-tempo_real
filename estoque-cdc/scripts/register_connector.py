from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
CONNECT_URL = os.getenv(
    "KAFKA_CONNECT_URL",
    "http://localhost:8083",
).rstrip("/")

CONFIG_PATH = (
    ROOT_DIR
    / "infra"
    / "debezium"
    / "postgres-connector.json"
)

ENV_PATH = (
    ROOT_DIR
    / "infra"
    / "debezium"
    / "connector.env"
)

FILE_PROVIDER_PATTERN = re.compile(
    r"\$\{file:/config/connector\.env:([A-Z0-9_]+)\}"
)


def carregar_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise FileNotFoundError(
            "Arquivo de configuração do Debezium não encontrado: "
            f"{path}"
        )

    values: dict[str, str] = {}

    for raw_line in path.read_text(
        encoding="utf-8-sig"
    ).splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if "=" not in line:
            raise ValueError(
                f"Linha inválida em {path.name}: {raw_line!r}"
            )

        key, value = line.split("=", 1)

        values[key.strip()] = (
            value
            .strip()
            .strip('"')
            .strip("'")
        )

    return values


def resolver_valor(
    value: Any,
    env_values: dict[str, str],
) -> Any:
    if not isinstance(value, str):
        return value

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = env_values.get(key)

        if resolved is None or resolved == "":
            relative_path = ENV_PATH.relative_to(ROOT_DIR)

            raise ValueError(
                f"A variável {key} não foi definida em "
                f"{relative_path}"
            )

        return resolved

    return FILE_PROVIDER_PATTERN.sub(replace, value)


def carregar_payload() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"JSON do conector não encontrado: {CONFIG_PATH}"
        )

    payload = json.loads(
        CONFIG_PATH.read_text(encoding="utf-8-sig")
    )

    # AVISO: no monorepo, as variáveis podem vir diretamente do Docker Compose.
    env_values = carregar_env(ENV_PATH) if ENV_PATH.exists() else {}
    for key in ("OLTP_HOST", "OLTP_PORT", "OLTP_DATABASE", "OLTP_USER", "OLTP_PASSWORD"):
        value = os.getenv(key)
        if value:
            env_values[key] = value

    config = payload.get("config")

    if not isinstance(config, dict):
        raise ValueError(
            "postgres-connector.json não possui "
            "o objeto 'config'."
        )

    payload["config"] = {
        key: resolver_valor(value, env_values)
        for key, value in config.items()
    }

    return payload


def aguardar_connect() -> None:
    last_error: Exception | None = None

    for _ in range(60):
        try:
            response = requests.get(
                f"{CONNECT_URL}/connector-plugins",
                timeout=3,
            )

            if response.ok:
                plugins = response.json()

                classes = {
                    plugin.get("class")
                    for plugin in plugins
                }

                expected = (
                    "io.debezium.connector.postgresql."
                    "PostgresConnector"
                )

                if expected not in classes:
                    raise RuntimeError(
                        "Kafka Connect está disponível, mas o "
                        "plugin PostgreSQL do Debezium não foi "
                        "encontrado."
                    )

                return

        except (
            requests.RequestException,
            ValueError,
            RuntimeError,
        ) as exc:
            last_error = exc

        time.sleep(2)

    raise RuntimeError(
        "Kafka Connect não ficou disponível corretamente: "
        f"{last_error}"
    )


def erro_connect(
    response: requests.Response,
) -> RuntimeError:
    try:
        detail = json.dumps(
            response.json(),
            ensure_ascii=False,
            indent=2,
        )
    except ValueError:
        detail = response.text or "Resposta sem corpo."

    return RuntimeError(
        "Kafka Connect recusou a configuração "
        f"(HTTP {response.status_code}).\n"
        f"{detail}"
    )


def main() -> None:
    aguardar_connect()

    payload = carregar_payload()
    name = str(payload["name"])

    existing = requests.get(
        f"{CONNECT_URL}/connectors/{name}",
        timeout=5,
    )

    if existing.status_code == 200:
        response = requests.put(
            f"{CONNECT_URL}/connectors/{name}/config",
            json=payload["config"],
            timeout=30,
        )
        action = "atualizado"

    elif existing.status_code == 404:
        response = requests.post(
            f"{CONNECT_URL}/connectors",
            json=payload,
            timeout=30,
        )
        action = "registrado"

    else:
        raise erro_connect(existing)

    if not response.ok:
        raise erro_connect(response)

    print(
        f"✅ Conector {name} {action} com sucesso."
    )


if __name__ == "__main__":
    main()