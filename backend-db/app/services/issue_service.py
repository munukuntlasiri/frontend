from sqlalchemy.orm import Session

from app.models import Issue


CATEGORY_KEYWORDS = {
    "Pothole": [
        "pothole",
        "hole in road",
        "road hole",
        "damaged road"
    ],
    "Garbage": [
        "garbage",
        "trash",
        "waste",
        "rubbish",
        "dump"
    ],
    "Streetlight": [
        "streetlight",
        "street light",
        "lamp",
        "light not working",
        "broken light"
    ],
    "Drainage": [
        "drain",
        "drainage",
        "sewage",
        "overflowing drain"
    ],
    "Water Leakage": [
        "water leakage",
        "water leak",
        "leaking pipe",
        "pipe leakage"
    ],
    "Road Damage": [
        "broken road",
        "damaged road",
        "cracked road",
        "road damage"
    ],
    "Public Infrastructure": [
        "footpath",
        "bridge",
        "public toilet",
        "bus stop",
        "infrastructure"
    ]
}


def classify_issue(description: str) -> str:
    text = description.lower()

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return category

    return "Other"


def calculate_priority(category: str, description: str) -> str:
    text = description.lower()

    high_priority_words = [
        "danger",
        "accident",
        "fire",
        "injury",
        "emergency",
        "flood",
        "electric shock",
        "live wire"
    ]

    for word in high_priority_words:
        if word in text:
            return "High"

    if category in [
        "Water Leakage",
        "Drainage",
        "Road Damage"
    ]:
        return "High"

    if category in [
        "Pothole",
        "Streetlight",
        "Garbage"
    ]:
        return "Medium"

    return "Low"


def generate_ai_summary(
    category: str,
    priority: str,
    description: str
) -> str:

    return (
        f"AI classified this complaint as '{category}' "
        f"with '{priority}' priority. "
        f"Complaint details: {description}"
    )


def create_issue(
    db: Session,
    title: str,
    description: str,
    location: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    image_path: str | None = None
):

    category = classify_issue(description)

    priority = calculate_priority(
        category,
        description
    )

    ai_summary = generate_ai_summary(
        category,
        priority,
        description
    )

    issue = Issue(
        title=title,
        description=description,
        category=category,
        status="Reported",
        priority=priority,
        location=location,
        latitude=latitude,
        longitude=longitude,
        image_path=image_path,
        ai_summary=ai_summary
    )

    db.add(issue)
    db.commit()
    db.refresh(issue)

    return issue


def get_issue(
    db: Session,
    issue_id: int
):

    return (
        db.query(Issue)
        .filter(Issue.id == issue_id)
        .first()
    )


def get_all_issues(
    db: Session
):

    return (
        db.query(Issue)
        .order_by(Issue.created_at.desc())
        .all()
    )


def update_issue_status(
    db: Session,
    issue_id: int,
    status: str
):

    issue = get_issue(
        db,
        issue_id
    )

    if issue is None:
        return None

    issue.status = status

    db.commit()
    db.refresh(issue)

    return issue


def delete_issue(
    db: Session,
    issue_id: int
):

    issue = get_issue(
        db,
        issue_id
    )

    if issue is None:
        return None

    db.delete(issue)
    db.commit()

    return issue