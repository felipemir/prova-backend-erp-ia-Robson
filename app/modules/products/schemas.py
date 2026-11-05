from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.modules.stock.service import stock_status

class ProductFields(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    preco: Decimal = Field(ge=0, max_digits=12, decimal_places=2)

    @field_validator("nome")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value or value.isdecimal():
            raise ValueError("Nome deve conter texto e não pode ser apenas numérico")
        return value

class ProductCreate(ProductFields):
    quantidade_em_estoque: int = Field(ge=12, strict=True)

class ProductPatch(BaseModel):
    nome: str | None = Field(default=None, max_length=200)
    preco: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    quantidade_em_estoque: int | None = Field(default=None, ge=0, strict=True)

    @field_validator("nome")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value or value.isdecimal():
            raise ValueError("Nome deve conter texto e não pode ser apenas numérico")
        return value

    @model_validator(mode="after")
    def reject_null_updates(self):
        if any(getattr(self, key) is None for key in self.model_fields_set):
            raise ValueError("Não é permitido atualizar campos para null")
        return self

class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nome: str
    preco: Decimal
    quantidade_em_estoque: int
    data_criacao: datetime
    data_atualizacao: datetime
    situacao_estoque: str
    alerta: str | None = None

    @classmethod
    def from_product(cls, product):
        quantity = product.quantidade_em_estoque
        status = stock_status(quantity)
        messages = {"sem_estoque": "Produto indisponível", "ultimas_unidades": "Últimas unidades!", "estoque_baixo": "Estoque baixo"}
        return cls(id=product.id, nome=product.nome, preco=product.preco,
                   quantidade_em_estoque=quantity, data_criacao=product.data_criacao,
                   data_atualizacao=product.data_atualizacao, situacao_estoque=status,
                   alerta=messages.get(status))

class ProductPage(BaseModel):
    items: list[ProductOut]
    page: int
    page_size: int
    total: int
