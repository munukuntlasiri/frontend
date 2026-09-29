"""Environment-backed runtime configuration with local-development defaults."""

import os


def _positive_int(name: str, default: int) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a positive integer.") from exc
    if value <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return value


def _cors_origins() -> tuple[str, ...]:
    raw_value = os.getenv("CIVICRESOLVE_CORS_ORIGINS", "*")
    origins = tuple(origin.strip() for origin in raw_value.split(",") if origin.strip())
    return origins or ("*",)


CORS_ORIGINS = _cors_origins()
SIGLIP_MODEL_ID = os.getenv(
    "CIVICRESOLVE_SIGLIP_MODEL_ID",
    "google/siglip-base-patch16-224",
).strip() or "google/siglip-base-patch16-224"
MAX_UPLOAD_MB = _positive_int("CIVICRESOLVE_MAX_UPLOAD_MB", 10)
