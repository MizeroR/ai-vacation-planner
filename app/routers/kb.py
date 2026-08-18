from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.services.knowledge import kb
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/kb", tags=["Knowledge"])

class DocSchema(BaseModel):
    id: str
    title: str | None = None
    text: str

class QueryResult(BaseModel):
    meta: dict
    text: str
    distance: float

@router.post("/seed", status_code=201)
def seed_kb(docs: List[DocSchema], current_user=Depends(get_current_user)):
    """
    Seed/index a list of documents into the knowledge base.
    Protected: requires an authenticated user (JWT)
    """
    items = [d.dict() for d in docs]
    try:
        kb.add_documents(items)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    return {"indexed": len(items)}

@router.get("/query", response_model=List[QueryResult])
def query_kb(q: str, k: int = 3):
    """
    Query the knlowedge base for `q`. Returns top-k chunks with distance and metadata.
    """
    results = kb.query(q, top_k=k)
    return results
