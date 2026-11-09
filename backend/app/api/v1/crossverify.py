"""Cross-verification API endpoints for comparing documents (PDF <-> PDF, PDF <-> Excel)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.schemas.crossverify import (
    CrossVerificationReport,
    CrossVerificationRequest,
)
from app.services.verification.cross_verifier import (
    find_and_verify_counterparts,
    verify_document_pair,
)

router = APIRouter(prefix="/crossverify", tags=["crossverify"])


@router.post(
    "",
    response_model=CrossVerificationReport,
    summary="Cross-verify two documents (e.g. PDF invoice against Excel spreadsheet record).",
)
async def cross_verify_documents_endpoint(
    payload: CrossVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
) -> CrossVerificationReport:
    """Compare extracted financial amounts, dates, and line items between two documents."""
    return await verify_document_pair(
        doc_a_id=payload.document_id_a,
        doc_b_id=payload.document_id_b,
        db=db,
    )


@router.get(
    "/{document_id}",
    response_model=list[CrossVerificationReport],
    summary="Find and cross-verify all candidate counterpart documents matching invoice number.",
)
async def get_counterpart_cross_verifications(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_session),
) -> list[CrossVerificationReport]:
    """Find other documents in the database matching invoice number and report cross-verification."""
    return await find_and_verify_counterparts(document_id=document_id, db=db)
