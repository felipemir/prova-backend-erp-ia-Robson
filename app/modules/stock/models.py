from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class StockAlert(Base):
    __tablename__ = "stock_alerts"
    __table_args__ = (UniqueConstraint("event_key", name="uq_stock_alert_event_key"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    previous_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    current_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_status: Mapped[str] = mapped_column(String(32), nullable=False)
    current_status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
