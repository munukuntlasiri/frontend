from app.db import SessionLocal, create_tables
from app.services.issue_service import create_issue


def seed_database():

    create_tables()

    db = SessionLocal()

    try:

        existing = db.query(
            __import__(
                "app.models",
                fromlist=["Issue"]
            ).Issue
        ).count()

        if existing > 0:

            print(
                "Database already contains issues."
            )

            return

        create_issue(
            db=db,
            title="Large pothole near main road",
            description=(
                "There is a large pothole on the "
                "main road causing danger to vehicles."
            ),
            location="Hyderabad"
        )

        create_issue(
            db=db,
            title="Garbage accumulation",
            description=(
                "Garbage and waste are accumulating "
                "near the residential area."
            ),
            location="Warangal"
        )

        create_issue(
            db=db,
            title="Broken streetlight",
            description=(
                "The streetlight is not working "
                "and the road is very dark at night."
            ),
            location="Hyderabad"
        )

        print(
            "Sample civic issues inserted successfully."
        )

    finally:

        db.close()


if __name__ == "__main__":

    seed_database()