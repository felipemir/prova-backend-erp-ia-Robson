from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.modules.agent.interpreter import interpretar
from app.modules.agent.repository import consultar_produtos
from app.modules.agent.schemas import AgentFilter, AgentResponse
from app.modules.products.schemas import ProductOut

LIMITE_RESULTADOS = 50

def responder(pergunta: str, db: Session) -> AgentResponse:
    try:
        consulta = interpretar(pergunta)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    produtos, total = consultar_produtos(db, consulta, limite=LIMITE_RESULTADOS)
    descricao_campo = "preço" if consulta.campo == "preco" else "estoque"
    descricao_operador = {"<": "abaixo de", "<=": "no máximo", ">": "acima de", ">=": "no mínimo", "=": "igual a"}[consulta.operador]
    descricao_filtro = f"{descricao_campo} {descricao_operador} {consulta.valor}"
    situacao = "encontrado" if total else "sem_resultados"
    mensagem = (
        f"{total} produto(s) encontrado(s) para {descricao_filtro}."
        if total else f"Nenhum produto encontrado para {descricao_filtro}."
    )
    return AgentResponse(
        intencao=consulta.intencao,
        filtros=[AgentFilter(campo=consulta.campo, operador=consulta.operador, valor=consulta.valor)],
        situacao=situacao,
        mensagem=mensagem,
        total=total,
        produtos=[ProductOut.from_product(produto) for produto in produtos],
        limite=LIMITE_RESULTADOS,
    )
