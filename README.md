# 🏥 Sistema de Estoque de Medicamentos com CDC em Tempo Real (CH-UFC)
 
![Status](https://img.shields.io/badge/Status-MVP%20Conclu%C3%ADdo-success)
![Python](https://img.shields.io/badge/Python-3.12+-blue)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)
![Kafka](https://img.shields.io/badge/Apache_Kafka-Streaming-black)
![Debezium](https://img.shields.io/badge/Debezium-CDC-red)
![Postgres](https://img.shields.io/badge/PostgreSQL-OLTP-336791)
![Redis](https://img.shields.io/badge/Redis-In--Memory_Cache-DC382D)
 
Monorepo com o **Banco OLTP** e o **pipeline CDC** de um sistema de estoque hospitalar. Execução local via Docker.

Repositório: [sistema-estoque-tempo_real](https://github.com/EXTENSAO-CHUFC/sistema-estoque-tempo_real)

## Arquitetura

```text
FastAPI / Simulador → PostgreSQL OLTP → (CDC) Debezium → Kafka → Consumer CDC → Redis → Dashboard
```

## Pré-requisitos

- Docker + Docker Compose v2
- Git

Não é necessário instalar Python, PostgreSQL, Kafka, Redis ou Poetry localmente — tudo roda em container.

Tenha em mente que essa é a versão com uma execução mais simples ou seja o usuario necessita
apenas executar o docker compose up para que a aplicação funcione pois tudo está contaneirizado.
SE QUISER UTILIZAR O DESENVOLVIMENTO FORA DE CONTAINERS FAÇA OS PASSOS ABAIXO.

**Opcional (desenvolvimento fora de container):** Python 3.12.10 (via pyenv) e Poetry 2.4.1. Cada módulo (`banco-oltp/`, `estoque-cdc/`) tem seu próprio `pyproject.toml`/`poetry.lock`:

```bash
pyenv install 3.12.10
pyenv local 3.12.10
python --version
```

```bash
cd banco-oltp && poetry install     # ou 
cd estoque-cdc && poetry install
```

## Executar

```bash
git clone https://github.com/EXTENSAO-CHUFC/sistema-estoque-tempo_real.git
cd sistema-estoque-tempo_real
docker compose up -d --build
docker compose ps
```

Na primeira subida, `oltp-bootstrap` cria o schema e carrega os seeds (sem apagar dados existentes), e `register-connector` registra o conector Debezium automaticamente. Ambos aparecem como `Exited (0)` depois — é esperado.

## Endereços locais
Essa versão não possui redirecionamento automatico, acesse os serviços por meio dos endereços:
| Serviço | Endereço |
|---|---|
| Banco OLTP / FastAPI | http://localhost:8000 |
| Health check | http://localhost:8000/health |
| Dashboard | http://localhost:8501 |
| Kafka Connect | http://localhost:8083 |


## Fluxo demonstrado

`simulador-saidas` registra uma saída aleatória a cada 15s no OLTP. O Debezium captura o WAL, o Kafka entrega ao `consumer-cdc`, e o Redis atualiza o dashboard.

Quando o estoque de um medicamento atinge o mínimo, o `consumer-cdc` publica no tópico `reabastecimento`; o `consumer-reabastecimento` (OLTP) consome de forma idempotente e cria uma nova entrada/lote.

## Persistência

Dados em volumes Docker (`postgres_data`, `kafka_data`, `redis_data`).

```bash
docker compose down       # preserva volumes
docker compose down -v    # apaga tudo — só use se quiser resetar de vez
```

## Comandos úteis

```bash
docker compose logs -f --tail=100                  # logs gerais
docker compose logs -f connect                     # Debezium/Kafka Connect
docker compose logs -f consumer-cdc                 # consumer CDC
docker compose logs -f consumer-reabastecimento     # reabastecimento
docker compose stop / start                         # pausar/retomar sem remover
```

## Configuração opcional

O Compose já tem defaults — `.env` não é obrigatório. Para customizar portas/limites/intervalo da simulação:
```bash
cp .env.example .env   # edite, depois: docker compose up -d
```

## Estrutura

```text
sistema-estoque-tempo_real/
├── docker-compose.yml
├── .env.example
├── banco-oltp/        # app, infra, scripts, Dockerfile, pyproject.toml
└── estoque-cdc/        # app, infra, scripts, Dockerfile, pyproject.toml
```

## Observação

Versão **local/acadêmica**. Não inclui integração com a VM Azure nem configuração de exposição pública — a versão de nuvem fica em repositório/branch de deploy separado.

## 👨🏻‍💻 Autor 
Francisco David Vaz de Sousa