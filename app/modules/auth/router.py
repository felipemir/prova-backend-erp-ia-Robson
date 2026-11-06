from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.modules.employees.models import Employee

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict[str, str]:
    employee = db.scalar(select(Employee).where(Employee.email == form.username.strip().lower()))
    if not employee or not employee.ativo or not verify_password(form.password, employee.password_hash):
        raise HTTPException(401, "Usuário ou senha inválidos", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": create_access_token(employee), "token_type": "bearer"}
