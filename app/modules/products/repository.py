from decimal import Decimal
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.modules.products.models import Product

def get_product(db: Session, product_id: int) -> Product | None:
    return db.get(Product, product_id)

def list_products(db: Session, page: int, page_size: int, nome: str | None,
                  preco_min: Decimal | None, preco_max: Decimal | None,
                  estoque_baixo: bool) -> tuple[list[Product], int]:
    query = select(Product)
    if nome:
        query = query.where(Product.nome.ilike(f"%{nome}%"))
    if preco_min is not None:
        query = query.where(Product.preco >= preco_min)
    if preco_max is not None:
        query = query.where(Product.preco <= preco_max)
    if estoque_baixo:
        query = query.where(Product.quantidade_em_estoque <= 12)
    count = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(query.order_by(Product.id).offset((page - 1) * page_size).limit(page_size)).all()
    return list(items), count
