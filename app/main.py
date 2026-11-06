from fastapi import FastAPI
from app.modules.agent.router import router as agent_router
from app.modules.products.router import router as products_router
from app.modules.stock.router import router as stock_router
from app.modules.orders.router import router as orders_router
from app.modules.employees.router import router as employees_router
from app.modules.auth.router import router as auth_router

app = FastAPI(title="ERP Backend - Prova Prática")
app.include_router(products_router)
app.include_router(stock_router)
app.include_router(orders_router)
app.include_router(employees_router)
app.include_router(auth_router)
app.include_router(agent_router)

@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
