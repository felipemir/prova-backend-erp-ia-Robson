"""Questão 8: interpretação determinística + consulta com banco de teste SQLite."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import get_current_employee
from app.main import app
from app.modules.agent.interpreter import interpretar
from app.modules.products.models import Product


@pytest.mark.parametrize(
    ("texto", "campo", "operador", "valor"),
    [
        ("Estoque abaixo de 5 unidades", "quantidade_em_estoque", "<", 5),
        ("Quantidade em estoque no mínimo 15", "quantidade_em_estoque", ">=", 15),
        ("Estoque no máximo 10", "quantidade_em_estoque", "<=", 10),
        ("Estoque igual a 0", "quantidade_em_estoque", "=", 0),
        ("Preço superior a 200 reais", "preco", ">", Decimal("200")),
        ("Preço inferior a 150,90 reais", "preco", "<", Decimal("150.90")),
        ("Preço exatamente 80 reais", "preco", "=", Decimal("80")),
        ("Preço no mínimo 99.90", "preco", ">=", Decimal("99.90")),
    ],
)
def test_interpretador(texto, campo, operador, valor):
    consulta = interpretar(texto)
    assert (consulta.campo, consulta.operador, consulta.valor) == (campo, operador, valor)


@pytest.mark.parametrize(
    "texto",
    [
        "Quais produtos estão disponíveis?",
        "Quero produtos abaixo de 5",
        "Estoque abaixo de 5 e preço acima de 100",
        "Estoque abaixo de 5 ou preço acima de 100",
        "Não quero estoque abaixo de 5",
        "Estoque abaixo de 5.5",
        "Preço acima de 1.000,00",
        "Preço acima de 100 e com qualquer nome",
    ],
)
def test_entrada_nao_suportada(texto):
    with pytest.raises(ValueError):
        interpretar(texto)


@pytest.fixture
def client_bd():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Product.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker.begin() as db:
        db.add_all([
            Product(nome="Mouse sem fio", preco=Decimal("149.90"), quantidade_em_estoque=8),
            Product(nome="Headset USB", preco=Decimal("249.90"), quantidade_em_estoque=3),
            Product(nome="Webcam", preco=Decimal("80.00"), quantidade_em_estoque=0),
        ])

    def banco_teste():
        with maker() as db:
            yield db

    app.dependency_overrides[get_db] = banco_teste
    app.dependency_overrides[get_current_employee] = lambda: object()
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_consulta_estoque_realmente_filtra(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": "Estoque abaixo de 5"})
    assert response.status_code == 200
    data = response.json()
    assert data["intencao"] == "consultar_estoque"
    assert data["filtros"] == [{"campo": "quantidade_em_estoque", "operador": "<", "valor": 5}]
    assert data["total"] == 2
    assert data["situacao"] == "encontrado"
    assert "2 produto(s)" in data["mensagem"]
    assert [p["nome"] for p in data["produtos"]] == ["Headset USB", "Webcam"]


def test_consulta_preco_decimal(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": "Preço acima de 149,90"})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["situacao"] == "encontrado"
    assert response.json()["produtos"][0]["nome"] == "Headset USB"


def test_ambiguidade_retorna_422(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": "Estoque abaixo de 5 e preço acima de 100"})
    assert response.status_code == 422


def test_json_pergunta_vazia_retorna_422(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": ""})
    assert response.status_code == 422


def test_consulta_valida_sem_resultados_retorna_200_e_mensagem(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": "Preço abaixo de 50"})
    assert response.status_code == 200
    data = response.json()
    assert data["intencao"] == "consultar_produtos"
    assert data["filtros"] == [{"campo": "preco", "operador": "<", "valor": "50"}]
    assert data["situacao"] == "sem_resultados"
    assert data["total"] == 0
    assert data["produtos"] == []
    assert "Nenhum produto encontrado" in data["mensagem"]


def test_pergunta_nao_suportada_retorna_exemplo_util(client_bd):
    response = client_bd.post("/agent/query", json={"pergunta": "Qual produto é o mais caro?"})
    assert response.status_code == 422
    assert "Exemplos:" in response.json()["detail"]
    assert "Preço acima de 200" in response.json()["detail"]
