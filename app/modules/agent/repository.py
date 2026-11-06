"""Consulta somente leitura: allowlist de colunas e operadores SQLAlchemy."""
from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.modules.products.models import Product
from app.modules.agent.interpreter import ConsultaInterpretada

COLUNAS = {
    "preco": Product.preco,
    "quantidade_em_estoque": Product.quantidade_em_estoque,
}

def consultar_produtos(db: Session, consulta: ConsultaInterpretada, limite: int = 50) -> tuple[list[Product], int]:
    coluna = COLUNAS[consulta.campo]
    comparacoes = {
        "<": coluna.__lt__,
        "<=": coluna.__le__,
        ">": coluna.__gt__,
        ">=": coluna.__ge__,
        "=": coluna.__eq__,
    }
    condicao = comparacoes[consulta.operador](consulta.valor)
    query = select(Product).where(condicao)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    produtos = db.scalars(query.order_by(Product.id).limit(limite)).all()
    return list(produtos), total
