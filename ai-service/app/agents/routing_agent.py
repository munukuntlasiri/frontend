"""Route classified civic issues using configurable department mappings."""


DEPARTMENT_BY_CATEGORY: dict[str, str] = {
    "Road Damage": "Road Maintenance Department",
    "Waste Management": "Sanitation / Waste Management Department",
    "Drainage": "Drainage / Sewerage Department",
    "Water Supply": "Water Supply Department",
    "Streetlight": "Electrical / Street Lighting Department",
    "Other": "Civic Services Review Desk",
}

DEFAULT_DEPARTMENT = "Civic Services Review Desk"


def route_department(category: str) -> str:
    """Return the configured department for a classified category."""

    return DEPARTMENT_BY_CATEGORY.get(category, DEFAULT_DEPARTMENT)
