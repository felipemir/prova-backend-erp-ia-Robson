from fastapi import FastAPI

from app.modules.products.router import router as products_router
from app.modules.stock.router import router as stock_router

app = FastAPI(title="ERP Backend - Prova Prática")

app.include_router(products_router)
app.include_router(stock_router)


@app.get("/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
