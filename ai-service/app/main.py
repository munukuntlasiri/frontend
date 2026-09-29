"""Application entry point for the CivicResolve AI service."""

import logging

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import run_in_threadpool

from app.agents.vision_agent import (
    MAX_UPLOAD_BYTES,
    InvalidImageError,
    OversizedImageError,
    UnsupportedImageMediaTypeError,
    VisionAgent,
    VisionProviderError,
)
from app.agents.resolution_agent import (
    ResolutionAgent,
    UnsupportedResolutionTargetError,
)
from app.config import CORS_ORIGINS
from app.models.schemas import (
    ComplaintAnalysis,
    ComplaintInput,
    DuplicateCheckRequest,
    DuplicateCheckResponse,
    FollowUpDecision,
    FollowUpRequest,
    HealthResponse,
    ResolutionVerification,
    VisionAnalysis,
)
from app.services.ai_service import (
    analyze_complaint as run_complaint_analysis,
    check_duplicate_candidates,
    evaluate_issue_follow_up,
)
from app.services.vision_service import get_resolution_agent, get_vision_agent

SERVICE_NAME = "CivicResolve AI"
SERVICE_VERSION = "0.1.0"
LOGGER = logging.getLogger(__name__)

app = FastAPI(
    title="CivicResolve AI - Agentic Intelligence Service",
    version=SERVICE_VERSION,
)

# The wildcard default keeps local demos simple. Integrated deployments must set
# CIVICRESOLVE_CORS_ORIGINS to an explicit comma-separated origin allowlist.
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Return basic service information."""

    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Report whether the API service is available."""

    return HealthResponse(
        status="healthy",
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
    )


@app.post("/analyze", response_model=ComplaintAnalysis)
async def analyze_complaint(complaint: ComplaintInput) -> ComplaintAnalysis:
    """Analyze a complaint with the local deterministic agent pipeline."""

    return run_complaint_analysis(complaint)


@app.post("/duplicate-check", response_model=DuplicateCheckResponse)
async def duplicate_check(request: DuplicateCheckRequest) -> DuplicateCheckResponse:
    """Compare a new report with candidate Master Civic Issues."""

    return check_duplicate_candidates(request)


@app.post("/follow-up", response_model=FollowUpDecision)
async def follow_up(request: FollowUpRequest) -> FollowUpDecision:
    """Evaluate one current issue snapshot for follow-up action."""

    return evaluate_issue_follow_up(request)


@app.post("/classify-image", response_model=VisionAnalysis)
async def classify_image(
    file: UploadFile = File(...),
    vision_agent: VisionAgent = Depends(get_vision_agent),
) -> VisionAnalysis:
    """Validate and classify independent photographic civic evidence."""

    try:
        image_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded image could not be read.",
        ) from exc
    finally:
        await file.close()

    try:
        return await run_in_threadpool(
            vision_agent.analyze,
            image_bytes,
            file.content_type,
        )
    except OversizedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except UnsupportedImageMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except VisionProviderError as exc:
        LOGGER.exception("Local vision provider failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc


@app.post("/verify-resolution", response_model=ResolutionVerification)
async def verify_resolution(
    before_file: UploadFile = File(...),
    after_file: UploadFile = File(...),
    category: str = Form(...),
    issue: str = Form(...),
    issue_id: str | None = Form(default=None),
    resolution_agent: ResolutionAgent = Depends(get_resolution_agent),
) -> ResolutionVerification:
    """Compare before/after evidence without changing backend issue state."""

    try:
        before_bytes = await before_file.read(MAX_UPLOAD_BYTES + 1)
        after_bytes = await after_file.read(MAX_UPLOAD_BYTES + 1)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One of the uploaded images could not be read.",
        ) from exc
    finally:
        await before_file.close()
        await after_file.close()

    try:
        return await run_in_threadpool(
            resolution_agent.verify,
            before_bytes,
            before_file.content_type,
            after_bytes,
            after_file.content_type,
            category,
            issue,
            issue_id,
        )
    except OversizedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=str(exc),
        ) from exc
    except UnsupportedImageMediaTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=str(exc),
        ) from exc
    except (InvalidImageError, UnsupportedResolutionTargetError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except VisionProviderError as exc:
        LOGGER.exception("Local vision provider failed during resolution verification")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
