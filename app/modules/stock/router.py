from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_employee
from app.modules.stock.models import StockAlert

router = APIRouter(prefix="/stock", tags=["stock"], dependencies=[Depends(get_current_employee)])

@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db), limit: int = 20) -> list[dict]:
    limit = min(max(limit, 1), 100)
    alerts = db.scalars(select(StockAlert).order_by(StockAlert.id.desc()).limit(limit)).all()
    return [{"id": a.id, "product_id": a.product_id, "previous_quantity": a.previous_quantity,
             "current_quantity": a.current_quantity, "previous_status": a.previous_status,
             "current_status": a.current_status, "created_at": a.created_at.isoformat()} for a in alerts]
