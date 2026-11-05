from fastapi import APIRouter
from app.modules.orders.schemas import OrderSummaryResponse
from app.modules.orders.service import get_order_summary

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}/summary", response_model=OrderSummaryResponse)
async def order_summary(order_id: str) -> OrderSummaryResponse:
    return await get_order_summary(order_id)
