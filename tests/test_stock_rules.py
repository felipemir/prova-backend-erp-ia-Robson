import pytest
from pydantic import ValidationError
from app.modules.stock.service import stock_status, alert_transition
from app.modules.products.schemas import ProductCreate, ProductPatch

@pytest.mark.parametrize("quantity,expected", [(0,"sem_estoque"),(1,"ultimas_unidades"),(5,"ultimas_unidades"),(6,"estoque_baixo"),(12,"estoque_baixo"),(13,"disponivel")])
def test_stock_bands(quantity, expected):
    assert stock_status(quantity) == expected

@pytest.mark.parametrize("old,new,expected", [(20,12,True),(12,11,False),(6,5,True),(3,0,True),(20,3,True),(5,20,False)])
def test_alert_transitions(old, new, expected):
    assert alert_transition(old, new) == expected

def test_minimum_on_create_only():
    with pytest.raises(ValidationError):
        ProductCreate(nome="Notebook", preco="10.20", quantidade_em_estoque=11)
    assert ProductCreate(nome="Notebook", preco="10.20", quantidade_em_estoque=12).quantidade_em_estoque == 12
    assert ProductPatch(quantidade_em_estoque=0).quantidade_em_estoque == 0

def test_invalid_data():
    for name in ["", "12345", "    "]:
        with pytest.raises(ValidationError):
            ProductCreate(nome=name, preco="10.00", quantidade_em_estoque=12)
    with pytest.raises(ValidationError):
        ProductCreate(nome="Mouse", preco="-1", quantidade_em_estoque=12)
    with pytest.raises(ValidationError):
        ProductPatch(nome=None)
