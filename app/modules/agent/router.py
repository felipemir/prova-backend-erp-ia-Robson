from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_employee
from app.modules.agent.schemas import AgentQuestion, AgentResponse
from app.modules.agent.service import responder

router = APIRouter(prefix="/agent", tags=["agent"], dependencies=[Depends(get_current_employee)])

@router.post("/query", response_model=AgentResponse)
def query(payload: AgentQuestion, db: Session = Depends(get_db)) -> AgentResponse:
    return responder(payload.pergunta, db)
