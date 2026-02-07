"""Modelos ORM SQLAlchemy 2.0 mapeando as tabelas existentes do banco pge_bi."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""
    pass


class ProcessoNovo(Base):
    """Processos jurídicos novos recebidos pela PGE."""

    __tablename__ = "processos_novos"

    id: Mapped[int] = mapped_column(primary_key=True)
    chefia: Mapped[str | None] = mapped_column(String(200))
    data: Mapped[datetime | None]
    codigo_processo: Mapped[str | None] = mapped_column(String(50))
    numero_processo: Mapped[int | None] = mapped_column(BigInteger)
    numero_formatado: Mapped[str | None] = mapped_column(Text)
    procurador: Mapped[str | None] = mapped_column(String(300))


class PecaElaborada(Base):
    """Peças jurídicas elaboradas pelos procuradores."""

    __tablename__ = "pecas_elaboradas"

    id: Mapped[int] = mapped_column(primary_key=True)
    chefia: Mapped[str | None] = mapped_column(String(200))
    data: Mapped[datetime | None]
    usuario_criacao: Mapped[str | None] = mapped_column(String(300))
    categoria: Mapped[str | None] = mapped_column(String(300))
    modelo: Mapped[str | None] = mapped_column(Text)
    numero_processo: Mapped[int | None] = mapped_column(BigInteger)
    numero_formatado: Mapped[str | None] = mapped_column(Text)
    procurador: Mapped[str | None] = mapped_column(String(300))


class Pendencia(Base):
    """Pendências associadas a processos jurídicos."""

    __tablename__ = "pendencias"

    id: Mapped[int] = mapped_column(primary_key=True)
    chefia: Mapped[str | None] = mapped_column(String(200))
    data: Mapped[datetime | None]
    numero_processo: Mapped[int | None] = mapped_column(BigInteger)
    numero_formatado: Mapped[str | None] = mapped_column(Text)
    area: Mapped[str | None] = mapped_column(String(100))
    procurador: Mapped[str | None] = mapped_column(String(300))
    usuario_cumpridor_pendencia: Mapped[str | None] = mapped_column(String(300))
    categoria: Mapped[str | None] = mapped_column(String(300))
    categoria_pendencia: Mapped[str | None] = mapped_column(String(100))
    cd_pendencia: Mapped[int | None] = mapped_column(BigInteger)


class PecaFinalizada(Base):
    """Peças jurídicas finalizadas."""

    __tablename__ = "pecas_finalizadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    chefia: Mapped[str | None] = mapped_column(String(200))
    data_finalizacao: Mapped[datetime | None]
    usuario_finalizacao: Mapped[str | None] = mapped_column(String(300))
    categoria: Mapped[str | None] = mapped_column(String(300))
    modelo: Mapped[str | None] = mapped_column(Text)
    numero_processo: Mapped[int | None] = mapped_column(BigInteger)
    numero_formatado: Mapped[str | None] = mapped_column(Text)
    procurador: Mapped[str | None] = mapped_column(String(300))


class UserRole(Base):
    """Classificação de usuários como procurador ou assessor."""

    __tablename__ = "user_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(300), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    carga_reduzida: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class ProcuradorLotacao(Base):
    """Lotação de procuradores em chefias (1 procurador → N chefias)."""

    __tablename__ = "procurador_lotacoes"

    id: Mapped[int] = mapped_column(primary_key=True)
    procurador: Mapped[str] = mapped_column(String(300), nullable=False)
    chefia: Mapped[str] = mapped_column(String(200), nullable=False)
    updated_at: Mapped[datetime | None] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("procurador", "chefia"),)


# Mapeamento de nome da tabela para modelo ORM
TABLE_MODEL_MAP: dict[str, type[Base]] = {
    "processos_novos": ProcessoNovo,
    "pecas_elaboradas": PecaElaborada,
    "pendencias": Pendencia,
    "pecas_finalizadas": PecaFinalizada,
}
