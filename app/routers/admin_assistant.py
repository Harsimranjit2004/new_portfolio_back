from fastapi import APIRouter, BackgroundTasks, Depends
from pymongo.database import Database

from ..database import get_db
from ..dependencies import require_admin
from ..schemas import ContentAssistantRequest, ContentAssistantResponse, ExecuteProposalRequest, ExecuteProposalResponse
from ..services.content_assistant import execute_content_proposal, plan_content
from ..services.knowledge_refresh import refresh_source_task

router = APIRouter(prefix="/admin-assistant", tags=["admin-assistant"], dependencies=[Depends(require_admin)])


@router.post("/chat", response_model=ContentAssistantResponse)
async def chat_with_content_helper(payload: ContentAssistantRequest, db: Database = Depends(get_db)):
    return await plan_content(db, payload)


@router.post("/execute", response_model=ExecuteProposalResponse)
def execute_proposal(payload: ExecuteProposalRequest, tasks: BackgroundTasks, db: Database = Depends(get_db)):
    result, source_type = execute_content_proposal(db, payload.proposal)
    tasks.add_task(refresh_source_task, source_type)
    return result
