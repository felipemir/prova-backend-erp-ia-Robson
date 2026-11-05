import os
from datetime import datetime, timedelta, timezone
import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.modules.employees.models import Employee

hasher = PasswordHasher()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def hash_password(password: str) -> str:
    return hasher.hash(password)

def verify_password(password: str, hashed: str) -> bool:
    try:
        return hasher.verify(hashed, password)
    except (VerifyMismatchError, VerificationError):
        return False

def _secret() -> str:
    value = os.getenv("JWT_SECRET", "")
    if len(value) < 32:
        raise RuntimeError("JWT_SECRET deve conter ao menos 32 caracteres")
    return value

def create_access_token(employee: Employee) -> str:
    expires = datetime.now(timezone.utc) + timedelta(minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "60")))
    return jwt.encode({"sub": str(employee.id), "exp": expires, "role": employee.role}, _secret(), algorithm="HS256")

def get_current_employee(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Employee:
    invalid = HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais inválidas ou token expirado", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, _secret(), algorithms=["HS256"])
        subject = payload.get("sub")
        if subject is None or not str(subject).isdigit():
            raise invalid
    except jwt.PyJWTError:
        raise invalid from None
    employee = db.get(Employee, int(subject))
    if employee is None or not employee.ativo:
        raise invalid
    return employee

def require_admin(employee: Employee = Depends(get_current_employee)) -> Employee:
    if employee.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão restrita ao administrador")
    return employee
