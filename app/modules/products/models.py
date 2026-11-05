from datetime import datetime
from decimal import Decimal
from sqlalchemy import CheckConstraint, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("preco >= 0", name="ck_products_preco_nonnegative"),
        CheckConstraint("quantidade_em_estoque >= 0", name="ck_products_stock_nonnegative"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    preco: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    quantidade_em_estoque: Mapped[int] = mapped_column(Integer, nullable=False)
    data_criacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    data_atualizacao: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
