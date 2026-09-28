import os
import shutil
from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile
)
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import (
    IssueCreate,
    IssueResponse,
    IssueUpdate
)
from app.services.issue_service import (
    create_issue,
    delete_issue,
    get_all_issues,
    get_issue,
    update_issue_status
)

router = APIRouter(
    prefix="/api",
    tags=["Civic Issues"]
)


UPLOAD_DIR = "uploads"

os.makedirs(
    UPLOAD_DIR,
    exist_ok=True
)


@router.get("/")
def api_home():
    return {
        "message": "CivicResolveAI API is running",
        "status": "success"
    }


@router.post(
    "/issues",
    response_model=IssueResponse
)
def create_civic_issue(
    title: str = Form(...),
    description: str = Form(...),
    location: Optional[str] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):

    image_path = None

    if image is not None:

        file_name = image.filename

        if not file_name:
            file_name = "uploaded_image"

        safe_file_name = os.path.basename(
            file_name
        )

        image_path = os.path.join(
            UPLOAD_DIR,
            safe_file_name
        )

        with open(
            image_path,
            "wb"
        ) as buffer:

            shutil.copyfileobj(
                image.file,
                buffer
            )

    issue = create_issue(
        db=db,
        title=title,
        description=description,
        location=location,
        latitude=latitude,
        longitude=longitude,
        image_path=image_path
    )

    return issue


@router.post(
    "/issues/json",
    response_model=IssueResponse
)
def create_civic_issue_json(
    issue_data: IssueCreate,
    db: Session = Depends(get_db)
):

    issue = create_issue(
        db=db,
        title=issue_data.title,
        description=issue_data.description,
        location=issue_data.location,
        latitude=issue_data.latitude,
        longitude=issue_data.longitude
    )

    return issue


@router.get(
    "/issues",
    response_model=list[IssueResponse]
)
def get_issues(
    db: Session = Depends(get_db)
):

    return get_all_issues(db)


@router.get(
    "/issues/{issue_id}",
    response_model=IssueResponse
)
def get_single_issue(
    issue_id: int,
    db: Session = Depends(get_db)
):

    issue = get_issue(
        db,
        issue_id
    )

    if issue is None:

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    return issue


@router.patch(
    "/issues/{issue_id}",
    response_model=IssueResponse
)
def update_issue(
    issue_id: int,
    issue_data: IssueUpdate,
    db: Session = Depends(get_db)
):

    issue = get_issue(
        db,
        issue_id
    )

    if issue is None:

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    if issue_data.status is not None:

        allowed_statuses = [
            "Reported",
            "Verified",
            "Assigned",
            "In Progress",
            "Resolved",
            "Rejected"
        ]

        if issue_data.status not in allowed_statuses:

            raise HTTPException(
                status_code=400,
                detail="Invalid status"
            )

        issue.status = issue_data.status

    if issue_data.priority is not None:

        allowed_priorities = [
            "Low",
            "Medium",
            "High"
        ]

        if issue_data.priority not in allowed_priorities:

            raise HTTPException(
                status_code=400,
                detail="Invalid priority"
            )

        issue.priority = issue_data.priority

    db.commit()
    db.refresh(issue)

    return issue


@router.delete(
    "/issues/{issue_id}"
)
def remove_issue(
    issue_id: int,
    db: Session = Depends(get_db)
):

    issue = delete_issue(
        db,
        issue_id
    )

    if issue is None:

        raise HTTPException(
            status_code=404,
            detail="Issue not found"
        )

    return {
        "message": "Issue deleted successfully",
        "issue_id": issue_id
    }