import asyncio


async def consultar_cliente(order_id: str) -> dict:
    await asyncio.sleep(0.1)
    return {"id": 101, "nome": "Cliente Exemplo", "pedido_consultado": order_id}


async def consultar_estoque(order_id: str) -> dict:
    await asyncio.sleep(0.2)
    return {"sku": "13527", "quantidade_disponivel": 8}


async def consultar_financeiro(order_id: str) -> dict:
    await asyncio.sleep(0.3)
    return {"situacao": "regular"}
