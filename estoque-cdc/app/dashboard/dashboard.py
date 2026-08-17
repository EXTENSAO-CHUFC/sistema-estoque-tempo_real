from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config.settings import settings
from app.services.cache_service import CacheService


st.set_page_config(
    page_title="HUWC | Estoque em tempo real",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Estilos

st.markdown(
    """
    <style>
        :root {
            --hospital-blue: #176b87;
            --hospital-blue-dark: #0f4c5c;
            --hospital-blue-light: #eaf6f9;
            --hospital-green: #2e8b74;
            --hospital-red: #c94c4c;
            --hospital-orange: #d97706;
            --surface: #ffffff;
            --surface-soft: #f5f9fb;
            --border: #d8e7ec;
            --text-primary: #16323c;
            --text-secondary: #5e737c;
        }

        .stApp {
            background:
                radial-gradient(circle at top right, rgba(23, 107, 135, 0.08), transparent 32rem),
                #f4f8fa;
        }

        [data-testid="stHeader"] {
            background: rgba(244, 248, 250, 0.88);
            backdrop-filter: blur(8px);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0f4c5c 0%, #176b87 100%);
        }

        [data-testid="stSidebar"] * {
            color: #ffffff;
        }

        .block-container {
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1500px;
        }

        .hospital-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 1.5rem;
            padding: 1.5rem 1.75rem;
            margin-bottom: 1.4rem;
            border: 1px solid var(--border);
            border-radius: 20px;
            background:
                linear-gradient(135deg, rgba(255,255,255,0.97), rgba(234,246,249,0.97));
            box-shadow: 0 12px 30px rgba(15, 76, 92, 0.08);
        }

        .hospital-brand {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .hospital-logo {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 58px;
            height: 58px;
            border-radius: 16px;
            background: linear-gradient(135deg, #176b87, #2e8b74);
            color: white;
            font-size: 1.8rem;
            box-shadow: 0 8px 18px rgba(23, 107, 135, 0.25);
        }

        .hospital-header h1 {
            margin: 0;
            color: var(--text-primary);
            font-size: clamp(1.55rem, 3vw, 2.25rem);
            line-height: 1.1;
        }

        .hospital-header p {
            margin: 0.45rem 0 0;
            color: var(--text-secondary);
            font-size: 0.96rem;
        }

        .live-status {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.65rem 0.95rem;
            border-radius: 999px;
            border: 1px solid #b7ddd3;
            background: #eaf8f3;
            color: #176b55;
            font-weight: 700;
            white-space: nowrap;
        }

        .live-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #2e8b74;
            box-shadow: 0 0 0 5px rgba(46, 139, 116, 0.13);
            animation: pulse 1.8s infinite;
        }

        @keyframes pulse {
            0%, 100% {
                opacity: 1;
            }

            50% {
                opacity: 0.45;
            }
        }

        .section-title {
            margin: 1.8rem 0 0.8rem;
            color: var(--text-primary);
            font-size: 1.25rem;
            font-weight: 800;
        }

        .section-subtitle {
            margin-top: -0.45rem;
            margin-bottom: 1rem;
            color: var(--text-secondary);
            font-size: 0.91rem;
        }

        [data-testid="stMetric"] {
            min-height: 128px;
            padding: 1.1rem 1.2rem;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: var(--surface);
            box-shadow: 0 8px 24px rgba(15, 76, 92, 0.06);
        }

        [data-testid="stMetricLabel"] {
            color: var(--text-secondary);
            font-weight: 700;
        }

        [data-testid="stMetricValue"] {
            color: var(--hospital-blue-dark);
            font-weight: 800;
        }

        [data-testid="stPlotlyChart"],
        [data-testid="stDataFrame"] {
            padding: 0.5rem;
            border: 1px solid var(--border);
            border-radius: 18px;
            background: var(--surface);
            box-shadow: 0 8px 24px rgba(15, 76, 92, 0.05);
            overflow: hidden;
        }

        div[data-testid="stAlert"] {
            border-radius: 14px;
        }

        .system-footer {
            margin-top: 2rem;
            padding: 1rem 1.2rem;
            border: 1px solid var(--border);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.75);
            color: var(--text-secondary);
            font-size: 0.88rem;
        }

        @media (max-width: 800px) {
            .hospital-header {
                align-items: flex-start;
                flex-direction: column;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# Utilidades

def medication_name_map(
    medications: list[dict[str, Any]],
) -> dict[int, str]:
    result: dict[int, str] = {}

    for item in medications:
        try:
            identifier = int(item["id"])
        except (KeyError, TypeError, ValueError):
            continue

        result[identifier] = str(
            item.get("nome") or f"Medicamento {identifier}"
        )

    return result


def build_stock_frame(
    lots: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for lote in lots:
        try:
            med_id = int(lote["medicamento_id"])
            quantity = int(lote.get("quantidade") or 0)
        except (KeyError, TypeError, ValueError):
            continue

        rows.append(
            {
                "medicamento_id": med_id,
                "medicamento": names.get(
                    med_id,
                    f"Medicamento {med_id}",
                ),
                "quantidade": quantity,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "medicamento_id",
                "medicamento",
                "estoque_total",
            ]
        )

    return (
        pd.DataFrame(rows)
        .groupby(
            ["medicamento_id", "medicamento"],
            as_index=False,
        )["quantidade"]
        .sum()
        .rename(
            columns={
                "quantidade": "estoque_total",
            }
        )
        .sort_values(
            "estoque_total",
            ascending=False,
        )
    )


def build_lots_frame(
    lots: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for lot in lots:
        try:
            medication_id = int(lot["medicamento_id"])
        except (KeyError, TypeError, ValueError):
            continue

        rows.append(
            {
                "Medicamento": names.get(
                    medication_id,
                    f"Medicamento {medication_id}",
                ),
                "Lote": lot.get("numero_lote") or "Não informado",
                "Almoxarifado": lot.get("almoxarifado_id") or "—",
                "Validade": lot.get("data_validade") or "—",
                "Quantidade": int(lot.get("quantidade") or 0),
            }
        )

    return pd.DataFrame(rows)


def build_movements_frame(
    movements: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for movement in movements:
        try:
            med_id = int(movement.get("medicamento_id"))
            quantity = int(movement.get("quantidade") or 0)
        except (TypeError, ValueError):
            continue

        rows.append(
            {
                "medicamento": names.get(
                    med_id,
                    f"Medicamento {med_id}",
                ),
                "tipo": str(
                    movement.get("tipo") or "DESCONHECIDO"
                ).upper(),
                "quantidade": quantity,
                "data_movimentacao": movement.get(
                    "data_movimentacao"
                ),
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=[
                "medicamento",
                "tipo",
                "quantidade",
                "data_movimentacao",
            ]
        )

    frame = pd.DataFrame(rows)

    frame["data_movimentacao"] = pd.to_datetime(
        frame["data_movimentacao"],
        errors="coerce",
        utc=True,
    )

    return frame.sort_values(
        "data_movimentacao",
        ascending=False,
    )


def build_alerts_frame(
    alerts: list[dict[str, Any]],
    names: dict[int, str],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for alert in alerts:
        try:
            med_id = int(
                alert.get("medicamento_id") or 0
            )
        except (TypeError, ValueError):
            continue

        created = alert.get("criado_em_epoch")

        try:
            created_at = (
                datetime.fromtimestamp(float(created))
                if created
                else None
            )
        except (TypeError, ValueError, OSError):
            created_at = None

        rows.append(
            {
                "Horário": created_at,
                "Medicamento": names.get(
                    med_id,
                    f"Medicamento {med_id}",
                ),
                "Estoque observado": alert.get(
                    "estoque_observado"
                ),
                "Quantidade solicitada": alert.get(
                    "quantidade_solicitada"
                ),
            }
        )

    return pd.DataFrame(rows)


def hospital_chart_layout(
    figure: go.Figure,
    title: str,
) -> go.Figure:
    figure.update_layout(
        title={
            "text": title,
            "x": 0.02,
            "xanchor": "left",
            "font": {"color": "#16323c"},
        },
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font={
            "family": "Arial, sans-serif",
            "color": "#16323c",
        },
        margin={
            "l": 25,
            "r": 25,
            "t": 60,
            "b": 25,
        },
        legend_title_text="",
        legend={"font": {"color": "#16323c"}},
        hoverlabel={
            "bgcolor": "#ffffff",
            "font_color": "#16323c",
        },
    )

    figure.update_xaxes(
        showgrid=False,
        linecolor="#d8e7ec",
        color="#16323c",
        tickfont={"color": "#16323c"},
    )

    figure.update_yaxes(
        gridcolor="#edf3f5",
        zeroline=False,
        color="#16323c",
        tickfont={"color": "#16323c"},
    )

    return figure


# Cabeçalho e menu lateral

st.markdown(
    """
    <div class="hospital-header">
        <div class="hospital-brand">
            <div class="hospital-logo">✚</div>
            <div>
                <h1>Central de Estoque Hospitalar</h1>
                <p>Monitoramento de medicamentos, lotes, movimentações e alertas em tempo real.</p>
            </div>
        </div>
        <div class="live-status">
            <span class="live-dot"></span>
            Monitoramento ativo
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("## 🏥 HUWC-Sistema de Estoque")
    st.caption("Controle operacional de medicamentos")

    st.divider()

    st.markdown("### Fluxo de dados")
    st.markdown(
        """
        **PostgreSQL OLTP**  
        ↓  
        **Debezium**  
        ↓  
        **Kafka**  
        ↓  
        **Consumer Python**  
        ↓  
        **Redis e Dashboard**
        """
    )

    st.divider()

    st.markdown("### Atualização")
    st.write(
        f"A cada **{settings.dashboard_refresh_seconds} "
        "segundo(s)**."
    )


# ---------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------

@st.fragment(
    run_every=f"{settings.dashboard_refresh_seconds}s"
)
def render_dashboard() -> None:
    try:
        cache = CacheService()

        health = cache.health()
        medications = cache.list_medications()
        lots = cache.list_lots()
        movements = cache.list_movements(limit=200)
        alerts = cache.list_alerts(limit=50)

    except Exception as exc:
        st.error(
            "Não foi possível acessar o Redis. "
            f"Detalhes: {exc}"
        )
        return

    names = medication_name_map(medications)

    stock = build_stock_frame(
        lots,
        names,
    )

    lots_frame = build_lots_frame(
        lots,
        names,
    )

    movement_frame = build_movements_frame(
        movements,
        names,
    )

    alerts_frame = build_alerts_frame(
        alerts,
        names,
    )

    total_stock = (
        int(stock["estoque_total"].sum())
        if not stock.empty
        else 0
    )

    low_stock_count = (
        int(
            (
                stock["estoque_total"]
                <= settings.minimum_stock
            ).sum()
        )
        if not stock.empty
        else 0
    )

    last_event = health.get("ultimo_evento")

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric(
        "Medicamentos",
        len(medications),
        help="Quantidade de medicamentos monitorados.",
    )

    c2.metric(
        "Unidades em estoque",
        f"{total_stock:,}".replace(",", "."),
        help="Soma das quantidades de todos os lotes.",
    )

    c3.metric(
        "Movimentações",
        len(movements),
        help="Entradas e saídas armazenadas no Redis.",
    )

    c4.metric(
        "Estoque baixo",
        low_stock_count,
        help=(
            "Medicamentos com estoque menor ou igual "
            f"a {settings.minimum_stock}."
        ),
    )

    c5.metric(
        "Eventos CDC",
        health.get("eventos_processados", 0),
        help="Eventos recebidos e processados do Kafka.",
    )

    # Visão geral do estoque

    st.markdown(
        '<div class="section-title">Visão geral do estoque</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Quantidade disponível consolidada por medicamento.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if stock.empty:
        st.info(
            "Aguardando eventos de medicamentos e lotes "
            "produzidos pelo Debezium."
        )
    else:
        stock_chart = px.bar(
            stock,
            x="medicamento",
            y="estoque_total",
            text="estoque_total",
            labels={
                "medicamento": "Medicamento",
                "estoque_total": "Quantidade",
            },
        )

        stock_chart.update_traces(
            marker_color="#176b87",
            marker_line_width=0,
            textposition="outside",
            textfont={"color": "#16323c"},
            cliponaxis=False,
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Estoque: %{y}<extra></extra>"
            ),
        )

        hospital_chart_layout(
            stock_chart,
            "Estoque por medicamento",
        )

        st.plotly_chart(
            stock_chart,
            use_container_width=True,
        )

        with st.expander(
            "Visualizar lotes detalhados",
            expanded=False,
        ):
            if lots_frame.empty:
                st.info("Nenhum lote disponível.")
            else:
                st.dataframe(
                    lots_frame,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Quantidade": st.column_config.NumberColumn(
                            "Quantidade",
                            format="%d unidade(s)",
                        ),
                    },
                )

    # -------------------------------------------------------------
    # Movimentações recentes
    # -------------------------------------------------------------

    st.markdown(
        '<div class="section-title">Movimentações recentes</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Últimas entradas e saídas registradas.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if movement_frame.empty:
        st.info(
            "Ainda não há movimentações processadas."
        )
    else:
        display_movements = movement_frame[
            [
                "data_movimentacao",
                "medicamento",
                "tipo",
                "quantidade",
            ]
        ].copy()

        display_movements.columns = [
            "Data e hora",
            "Medicamento",
            "Tipo",
            "Quantidade",
        ]

        st.dataframe(
            display_movements,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data e hora": st.column_config.DatetimeColumn(
                    "Data e hora",
                    format="DD/MM/YYYY HH:mm:ss",
                ),
                "Quantidade": st.column_config.NumberColumn(
                    "Quantidade",
                    format="%d unidade(s)",
                ),
            },
        )

    # Alertas de reabastecimento

    st.markdown(
        '<div class="section-title">Alertas de reabastecimento</div>',
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-subtitle">
            Solicitações automáticas geradas após detecção
            de estoque abaixo do limite.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if alerts_frame.empty:
        st.success(
            "Nenhum alerta de reabastecimento pendente."
        )
    else:
        st.warning(
            f"{len(alerts_frame)} alerta(s) encontrado(s)."
        )

        st.dataframe(
            alerts_frame,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Horário": st.column_config.DatetimeColumn(
                    "Horário",
                    format="DD/MM/YYYY HH:mm:ss",
                ),
            },
        )

    last_event_text = (
        str(last_event)
        if last_event
        else "nenhum evento recebido"
    )

    st.markdown(
        f"""
        <div class="system-footer">
            <strong>Status:</strong> Redis conectado
            &nbsp;·&nbsp;
            <strong>Atualização:</strong>
            a cada {settings.dashboard_refresh_seconds} segundo(s)
            &nbsp;·&nbsp;
            <strong>Último evento:</strong>
            {last_event_text}
        </div>
        """,
        unsafe_allow_html=True,
    )


render_dashboard()