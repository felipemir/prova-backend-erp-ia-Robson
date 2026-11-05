import json
import logging
from sqlalchemy.exc import IntegrityError
from app.core.database import SessionLocal
from app.modules.stock.models import StockAlert

logger = logging.getLogger(__name__)

def record_stock_alert(event_key: str, product_id: int, previous_quantity: int,
                       current_quantity: int, previous_status: str, current_status: str) -> None:
    with SessionLocal() as db:
        alert = StockAlert(event_key=event_key, product_id=product_id,
                           previous_quantity=previous_quantity, current_quantity=current_quantity,
                           previous_status=previous_status, current_status=current_status)
        db.add(alert)
        try:
            db.commit()
            db.refresh(alert)
        except IntegrityError:
            db.rollback()
            logger.info(json.dumps({"event": "stock.alert_duplicate", "event_key": event_key,
                                    "product_id": product_id}))
            return
        logger.info(json.dumps({"event": "stock.threshold_crossed", "event_key": event_key,
                                "product_id": product_id, "previous_quantity": previous_quantity,
                                "current_quantity": current_quantity, "previous_status": previous_status,
                                "current_status": current_status, "alert_id": alert.id, "result": "success"}))
