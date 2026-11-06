from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_employee, hash_password, require_admin
from app.modules.employees.models import Employee

router = APIRouter(prefix="/employees", tags=["employees"])

class EmployeeCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(min_length=10, max_length=128)
    role: str = Field(default="employee", pattern=r"^(admin|employee)$")

class EmployeeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    email: str
    role: str
    ativo: bool

@router.get("/me", response_model=EmployeeOut)
def me(employee: Employee = Depends(get_current_employee)) -> Employee:
    return employee

@router.post("", status_code=201, response_model=EmployeeOut)
def create_employee(data: EmployeeCreate, db: Session = Depends(get_db), _admin: Employee = Depends(require_admin)) -> Employee:
    email = str(data.email).lower()
    if db.scalar(select(Employee.id).where(Employee.email == email)) is not None:
        raise HTTPException(409, "E-mail já cadastrado")
    employee = Employee(nome=data.nome.strip(), email=email, password_hash=hash_password(data.senha), role=data.role)
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee
