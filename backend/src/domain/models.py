"""Modelos ORM SQLAlchemy 2.0 mapeando as tabelas existentes do banco pge_bi."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base para todos os modelos ORM."""
    pass


class ProcessoNovo(Base):
    """Processos jurídicos novos recebidos pela PGE."""

    __tablename__ = "processos_novos"

    id: Mapped[int] = mapped_column(primary_key=True)
    cd_processo: Mapped[str | None] = mapped_column(String(50))
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
    cd_documento: Mapped[int | None] = mapped_column(BigInteger)
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
    cd_documento: Mapped[int | None] = mapped_column(BigInteger)
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


class HiddenProcuradorProducao(Base):
    """Regra de ocultação temporária da produção de um procurador.

    Permite ao admin ocultar a produção de um procurador nas telas de chefia
    por um período específico, sem alterar dados no banco.
    """

    __tablename__ = "admin_hidden_procurador_producao"

    id: Mapped[int] = mapped_column(primary_key=True)
    procurador_name: Mapped[str] = mapped_column(String(300), nullable=False)
    chefia: Mapped[str | None] = mapped_column(String(200))  # NULL = global
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(
        String(100), nullable=False, server_default="admin"
    )
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(onupdate=func.now())

    __table_args__ = (
        Index(
            "ix_hidden_proc_active", "procurador_name", "chefia", "is_active"
        ),
        Index(
            "ix_hidden_dates_active",
            "chefia",
            "start_date",
            "end_date",
            "is_active",
        ),
        CheckConstraint("start_date <= end_date", name="ck_start_before_end"),
    )


class Assunto(Base):
    """Árvore hierárquica de assuntos jurídicos (até 9 níveis)."""

    __tablename__ = "assuntos"

    codigo: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    codigo_pai: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("assuntos.codigo"), index=True
    )
    nome: Mapped[str | None] = mapped_column(String(500))
    descricao: Mapped[str | None] = mapped_column(Text)
    nivel: Mapped[int | None] = mapped_column(SmallInteger)
    numero_fmt: Mapped[str | None] = mapped_column(String(50))


class ProcessoAssunto(Base):
    """Vínculo N:N entre processos e assuntos."""

    __tablename__ = "processo_assuntos"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_processo: Mapped[int] = mapped_column(BigInteger, nullable=False)
    codigo_assunto: Mapped[int] = mapped_column(
        Integer, ForeignKey("assuntos.codigo"), nullable=False
    )
    assunto_principal: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    __table_args__ = (
        Index("idx_proc_assuntos_numero", "numero_processo"),
        Index("idx_proc_assuntos_assunto", "codigo_assunto"),
    )


class AccessLog(Base):
    """Registro de acessos ao sistema BI."""

    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now())
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)


class ParteProcesso(Base):
    """Partes de um processo (autores, réus, advogados) extraídas do Oracle."""

    __tablename__ = "partes_processo"

    cd_processo: Mapped[str] = mapped_column(String(50), primary_key=True)
    seq_parte: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero_processo: Mapped[str | None] = mapped_column(String(50))
    numero_formatado: Mapped[str | None] = mapped_column(String(50))
    cd_pessoa: Mapped[int | None] = mapped_column(BigInteger)
    nome: Mapped[str | None] = mapped_column(Text)
    tipo_parte: Mapped[str | None] = mapped_column(Text)
    polo: Mapped[int | None] = mapped_column(Integer)
    principal: Mapped[str | None] = mapped_column(String(1))
    tipo_pessoa: Mapped[str | None] = mapped_column(String(1))
    cd_categ_pessoa: Mapped[int | None] = mapped_column(Integer)
    cpf: Mapped[str | None] = mapped_column(String(20))
    cnpj: Mapped[str | None] = mapped_column(String(20))
    rg: Mapped[str | None] = mapped_column(String(30))
    oab: Mapped[str | None] = mapped_column(String(30))
    valor_acao: Mapped[float | None]
    tipo_valor: Mapped[str | None] = mapped_column(String(1))


class ParteNormalizada(Base):
    """Partes normalizadas por CPF/CNPJ com métricas agregadas."""

    __tablename__ = "partes_normalizadas"

    id: Mapped[int] = mapped_column(primary_key=True)
    chave_tipo: Mapped[str] = mapped_column(String(4), nullable=False)
    chave_valor: Mapped[str] = mapped_column(Text, nullable=False)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    cpf: Mapped[str | None] = mapped_column(String(20))
    cnpj: Mapped[str | None] = mapped_column(String(20))
    oab: Mapped[str | None] = mapped_column(String(30))
    tipo_pessoa: Mapped[str | None] = mapped_column(String(1))
    qtd_processos: Mapped[int] = mapped_column(Integer, default=0)
    qtd_contra_estado: Mapped[int] = mapped_column(Integer, default=0)
    qtd_executado_estado: Mapped[int] = mapped_column(Integer, default=0)
    qtd_advogado: Mapped[int] = mapped_column(Integer, default=0)
    qtd_coreu_estado: Mapped[int] = mapped_column(Integer, default=0)
    valor_total: Mapped[float] = mapped_column(default=0)
    valor_medio: Mapped[float] = mapped_column(default=0)


# Mapeamento de nome da tabela para modelo ORM
TABLE_MODEL_MAP: dict[str, type[Base]] = {
    "processos_novos": ProcessoNovo,
    "pecas_elaboradas": PecaElaborada,
    "pendencias": Pendencia,
    "pecas_finalizadas": PecaFinalizada,
}
