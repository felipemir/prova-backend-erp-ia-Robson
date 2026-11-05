from fastapi import APIRouter, Response
from app.modules.orders.schemas import OrderSummaryResponse
from app.modules.orders.service import get_order_summary

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get(
    "/{order_id}/summary",
    response_model=OrderSummaryResponse,
    responses={503: {"model": OrderSummaryResponse}},
)
async def order_summary(order_id: str, response: Response) -> OrderSummaryResponse:
    summary = await get_order_summary(order_id)
    if summary.status == "unavailable":
        response.status_code = 503
    return summary
