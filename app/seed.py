"""Dados demonstrativos: insere registros ausentes, sem restaurar valores alterados."""
import os
from decimal import Decimal
from sqlalchemy import select
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.modules.employees.models import Employee
from app.modules.products.models import Product

PRODUCTS = [
    ("Notebook Acer", "3500.00", 30), ("Monitor LG", "899.90", 13),
    ("Teclado mecânico", "299.90", 12), ("Mouse sem fio", "149.90", 8),
    ("Headset USB", "249.90", 3), ("Webcam Full HD", "189.90", 0),
]

def seed() -> None:
    accounts = [
        ("Administrador Demo", os.environ["DEMO_ADMIN_EMAIL"], os.environ["DEMO_ADMIN_PASSWORD"], "admin"),
        ("Funcionário Demo", os.environ["DEMO_EMPLOYEE_EMAIL"], os.environ["DEMO_EMPLOYEE_PASSWORD"], "employee"),
    ]
    with SessionLocal.begin() as db:
        for name, email, password, role in accounts:
            if not db.scalar(select(Employee.id).where(Employee.email == email.lower())):
                db.add(Employee(nome=name, email=email.lower(), password_hash=hash_password(password), role=role))
        for name, price, quantity in PRODUCTS:
            if not db.scalar(select(Product.id).where(Product.nome == name)):
                db.add(Product(nome=name, preco=Decimal(price), quantidade_em_estoque=quantity))

if __name__ == "__main__":
    seed()
