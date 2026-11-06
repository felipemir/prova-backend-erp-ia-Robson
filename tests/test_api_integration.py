"""Integração real: executado com PostgreSQL e Redis do Compose."""
import os
import time
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import SessionLocal
from app.modules.products.models import Product
from app.modules.stock.models import StockAlert

def _token(client, email, password):
    r = client.post("/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}

def test_full_crud_permissions_cache_and_worker():
    with TestClient(app) as client:
        admin = _token(client, os.environ["DEMO_ADMIN_EMAIL"], os.environ["DEMO_ADMIN_PASSWORD"])
        employee = _token(client, os.environ["DEMO_EMPLOYEE_EMAIL"], os.environ["DEMO_EMPLOYEE_PASSWORD"])
        assert client.get("/employees/me", headers=employee).status_code == 200
        assert client.get("/products").status_code == 401
        assert client.post("/products", json={"nome": "Invalido", "preco": "10", "quantidade_em_estoque": 11}, headers=employee).status_code == 422
        title = f"Produto CI {uuid.uuid4().hex[:8]}"
        r = client.post("/products", json={"nome": title, "preco": "99.90", "quantidade_em_estoque": 20}, headers=employee)
        assert r.status_code == 201, r.text
        product_id = r.json()["id"]
        try:
            assert client.get(f"/products/{product_id}", headers=employee).status_code == 200
            assert client.get("/products", params={"nome": title, "page_size": 1}, headers=employee).json()["total"] >= 1
            assert client.delete(f"/products/{product_id}", headers=employee).status_code == 403
            r = client.patch(f"/products/{product_id}", json={"quantidade_em_estoque": 5}, headers=employee)
            assert r.status_code == 200, r.text
            assert r.json()["situacao_estoque"] == "ultimas_unidades"
            assert client.get(f"/products/{product_id}", headers=employee).json()["quantidade_em_estoque"] == 5
            assert client.get("/products", params={"estoque_baixo": "true"}, headers=employee).status_code == 200
            deadline = time.monotonic() + 15
            found = False
            while time.monotonic() < deadline:
                with SessionLocal() as db:
                    found = db.scalar(select(StockAlert.id).where(StockAlert.product_id == product_id)) is not None
                if found:
                    break
                time.sleep(0.2)
            assert found, "O worker RQ não registrou o alerta no PostgreSQL"
        finally:
            assert client.delete(f"/products/{product_id}", headers=admin).status_code == 204
            assert client.get(f"/products/{product_id}", headers=admin).status_code == 404

def test_seed_idempotent():
    from app.seed import seed
    with SessionLocal() as db:
        initial = db.query(Product).count()
    seed()
    with SessionLocal() as db:
        assert db.query(Product).count() == initial
