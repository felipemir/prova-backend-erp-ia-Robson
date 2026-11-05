from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session
from app.core.cache import cache_read, cache_write
from app.core.database import get_db
from app.core.security import get_current_employee, require_admin
from app.modules.products.repository import get_product, list_products
from app.modules.products.schemas import ProductCreate, ProductOut, ProductPage, ProductPatch
from app.modules.products.service import create_product, delete_product, update_product

router = APIRouter(prefix="/products", tags=["products"], dependencies=[Depends(get_current_employee)])

@router.post("", response_model=ProductOut, status_code=201)
def create(data: ProductCreate, db: Session = Depends(get_db)) -> ProductOut:
    return ProductOut.from_product(create_product(db, data))

@router.get("", response_model=ProductPage)
def listing(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
            nome: str | None = None, preco_min: Decimal | None = Query(None, ge=0),
            preco_max: Decimal | None = Query(None, ge=0), estoque_baixo: bool = False,
            db: Session = Depends(get_db)) -> ProductPage:
    if preco_min is not None and preco_max is not None and preco_min > preco_max:
        raise HTTPException(422, "preco_min não pode ser maior que preco_max")
    items, total = list_products(db, page, page_size, nome, preco_min, preco_max, estoque_baixo)
    return ProductPage(items=[ProductOut.from_product(p) for p in items], page=page, page_size=page_size, total=total)

@router.get("/{product_id}", response_model=ProductOut)
def detail(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    cached = cache_read(product_id)
    if cached is not None:
        return ProductOut.model_validate(cached)
    product = get_product(db, product_id)
    if not product:
        raise HTTPException(404, "Produto não encontrado")
    value = ProductOut.from_product(product)
    cache_write(product_id, value.model_dump(mode="json"))
    return value

@router.patch("/{product_id}", response_model=ProductOut)
def patch(product_id: int, data: ProductPatch, db: Session = Depends(get_db)) -> ProductOut:
    return ProductOut.from_product(update_product(db, product_id, data))

@router.delete("/{product_id}", status_code=204, dependencies=[Depends(require_admin)])
def delete(product_id: int, db: Session = Depends(get_db)) -> Response:
    delete_product(db, product_id)
    return Response(status_code=204)
