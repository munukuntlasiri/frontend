import sys
import os

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.insert(0, PROJECT_ROOT)

from app.db import create_tables


if __name__ == "__main__":
    create_tables()

    print("================================")
    print("CivicResolveAI database created")
    print("================================")