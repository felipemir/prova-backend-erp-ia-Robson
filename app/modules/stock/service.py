from enum import IntEnum

class StockBand(IntEnum):
    SEM_ESTOQUE = 0
    ULTIMAS_UNIDADES = 1
    ESTOQUE_BAIXO = 2
    DISPONIVEL = 3

STATUS_NAMES = {
    StockBand.SEM_ESTOQUE: "sem_estoque",
    StockBand.ULTIMAS_UNIDADES: "ultimas_unidades",
    StockBand.ESTOQUE_BAIXO: "estoque_baixo",
    StockBand.DISPONIVEL: "disponivel",
}

def stock_band(quantity: int) -> StockBand:
    if quantity < 0:
        raise ValueError("Quantidade não pode ser negativa")
    if quantity == 0:
        return StockBand.SEM_ESTOQUE
    if quantity <= 5:
        return StockBand.ULTIMAS_UNIDADES
    if quantity <= 12:
        return StockBand.ESTOQUE_BAIXO
    return StockBand.DISPONIVEL

def stock_status(quantity: int) -> str:
    return STATUS_NAMES[stock_band(quantity)]

def alert_transition(previous: int, current: int) -> bool:
    return stock_band(current) < stock_band(previous)
