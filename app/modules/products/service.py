import logging
from uuid import uuid4
from fastapi import HTTPException
from rq import Queue
from redis.exceptions import RedisError
from sqlalchemy.orm import Session
from app.core.cache import cache_invalidate, redis_client
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductPatch
from app.modules.products.repository import get_product
from app.modules.stock.service import alert_transition, stock_status

logger = logging.getLogger(__name__)

def create_product(db: Session, data: ProductCreate) -> Product:
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product

def update_product(db: Session, product_id: int, data: ProductPatch) -> Product:
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Produto não encontrado")
    previous = product.quantidade_em_estoque
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(product, key, value)
    # O commit precede a invalidação do cache e o enqueue: sem outbox,
    # uma falha no Redis pode deixar o estoque atualizado sem alerta.
    db.commit()
    db.refresh(product)
    cache_invalidate(product.id)
    current = product.quantidade_em_estoque
    if "quantidade_em_estoque" in changes and alert_transition(previous, current):
        key = uuid4().hex
        try:
            Queue("default", connection=redis_client()).enqueue(
                "app.workers.tasks.record_stock_alert", key, product.id, previous, current,
                stock_status(previous), stock_status(current), job_id=f"stock-alert-{key}",
            )
        except (RedisError, ConnectionError, OSError):
            logger.exception("Falha ao enfileirar alerta produto=%s, anterior=%s, atual=%s", product.id, previous, current)
    return product

def delete_product(db: Session, product_id: int) -> None:
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Produto não encontrado")
    db.delete(product)
    db.commit()
    cache_invalidate(product_id)
