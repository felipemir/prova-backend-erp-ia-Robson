from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, Field
from app.modules.products.schemas import ProductOut

class AgentQuestion(BaseModel):
    pergunta: str = Field(min_length=1, max_length=500)

class AgentFilter(BaseModel):
    campo: Literal["quantidade_em_estoque", "preco"]
    operador: Literal["<", ">", "=", "<=", ">="]
    valor: int | Decimal

class AgentResponse(BaseModel):
    intencao: Literal["consultar_estoque", "consultar_produtos"]
    filtros: list[AgentFilter]
    total: int
    produtos: list[ProductOut]
    limite: int
