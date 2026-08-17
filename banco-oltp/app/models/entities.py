from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config.database import Base


class Medicamento(Base):
    __tablename__ = "medicamentos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    principio_ativo: Mapped[str | None] = mapped_column(String(100))
    laboratorio: Mapped[str | None] = mapped_column(String(100))
    estoque_maximo: Mapped[int] = mapped_column(Integer, nullable=False, default=500)

    lotes: Mapped[list["Lote"]] = relationship(back_populates="medicamento")


class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    contato: Mapped[str | None] = mapped_column(String(100))

    lotes: Mapped[list["Lote"]] = relationship(back_populates="fornecedor")


class Almoxarifado(Base):
    __tablename__ = "almoxarifados"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    localizacao: Mapped[str | None] = mapped_column(String(200))

    lotes: Mapped[list["Lote"]] = relationship(back_populates="almoxarifado")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str | None] = mapped_column(String(20))

    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="usuario"
    )


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    medicamento_id: Mapped[int] = mapped_column(
        ForeignKey("medicamentos.id"), nullable=False
    )
    numero_lote: Mapped[str] = mapped_column(String(50), nullable=False)
    data_validade: Mapped[date] = mapped_column(Date, nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    almoxarifado_id: Mapped[int] = mapped_column(
        ForeignKey("almoxarifados.id"), nullable=False
    )
    fornecedor_id: Mapped[int] = mapped_column(
        ForeignKey("fornecedores.id"), nullable=False
    )

    medicamento: Mapped[Medicamento] = relationship(back_populates="lotes")
    almoxarifado: Mapped[Almoxarifado] = relationship(back_populates="lotes")
    fornecedor: Mapped[Fornecedor] = relationship(back_populates="lotes")
    movimentacoes: Mapped[list["Movimentacao"]] = relationship(
        back_populates="lote"
    )


class Movimentacao(Base):
    __tablename__ = "movimentacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    lote_id: Mapped[int] = mapped_column(
        ForeignKey("lotes.id"), nullable=False
    )
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, nullable=False)
    data_movimentacao: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    usuario_id: Mapped[int] = mapped_column(
        ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )

    lote: Mapped[Lote] = relationship(back_populates="movimentacoes")
    usuario: Mapped[Usuario] = relationship(back_populates="movimentacoes")


class EventoKafkaProcessado(Base):
    __tablename__ = "eventos_kafka_processados"

    evento_id: Mapped[str] = mapped_column(String(255), primary_key=True)
    topico: Mapped[str] = mapped_column(String(255), nullable=False)
    particao: Mapped[int] = mapped_column(Integer, nullable=False)
    offset_kafka: Mapped[int] = mapped_column(BigInteger, nullable=False)
    medicamento_id: Mapped[int] = mapped_column(
        ForeignKey("medicamentos.id"), nullable=False
    )
    lote_id: Mapped[int] = mapped_column(
        ForeignKey("lotes.id"), nullable=False
    )
    processado_em: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
