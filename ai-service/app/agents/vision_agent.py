"""Validate images and coordinate provider-independent civic vision analysis."""

from dataclasses import dataclass
from io import BytesIO
import math
from typing import Protocol, Sequence
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from app.config import MAX_UPLOAD_MB
from app.models.schemas import VisionAnalysis, VisionPrediction

MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_IMAGE_PIXELS = 40_000_000

SUPPORTED_IMAGE_FORMATS: dict[str, str] = {
    "image/jpeg": "JPEG",
    "image/png": "PNG",
    "image/webp": "WEBP",
}
IMAGE_MIME_ALIASES: dict[str, str] = {
    "image/jpg": "image/jpeg",
}
DECODED_FORMAT_MIME_TYPES: dict[str, str] = {
    decoded_format: mime_type
    for mime_type, decoded_format in SUPPORTED_IMAGE_FORMATS.items()
}

# Provisional MVP gates based on one validated pothole image. They require calibration
# against a broader, representative civic image dataset before production use.
MIN_CIVIC_RELATIVE_SCORE = 0.20
MIN_CONTROL_MARGIN = 0.10
MIN_RUNNER_UP_MARGIN = 0.10


class VisionInputError(ValueError):
    """Base error for invalid uploaded image evidence."""


class UnsupportedImageMediaTypeError(VisionInputError):
    """Raised when declared or decoded image media is unsupported."""


class OversizedImageError(VisionInputError):
    """Raised when uploaded bytes exceed the configured limit."""


class InvalidImageError(VisionInputError):
    """Raised when uploaded bytes are empty, corrupt, or unsafe to decode."""


class VisionProviderError(RuntimeError):
    """Raised when a vision provider cannot load or perform inference."""


class VisionProvider(Protocol):
    """Replaceable boundary for local or future approved vision providers."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def device(self) -> str: ...

    def score_prompts(self, image: Image.Image, prompts: Sequence[str]) -> list[float]:
        """Return one relative score for every prompt in the same order."""


@dataclass(frozen=True)
class VisionCategoryConfig:
    """One visual issue with taxonomy and backward-compatible API labels."""

    label: str
    category: str
    issue: str | None
    taxonomy_category: str
    taxonomy_issue: str | None
    prompts: tuple[str, ...]
    is_control: bool = False
    automatic_resolution_supported: bool = False


VISION_CATEGORIES: tuple[VisionCategoryConfig, ...] = (
    VisionCategoryConfig(
        label="Road Damage / Pothole",
        category="Road Damage",
        issue="Pothole",
        taxonomy_category="Road",
        taxonomy_issue="Pothole",
        prompts=(
            "a photo of a pothole in a road",
            "a localized deep hole with missing asphalt in a road surface",
            "a bowl-shaped roadway cavity with broken asphalt edges",
        ),
        automatic_resolution_supported=True,
    ),
    VisionCategoryConfig(
        label="Road / Cracked Road",
        category="Road Damage",
        issue="Cracked Road",
        taxonomy_category="Road",
        taxonomy_issue="Cracked Road",
        prompts=(
            "multiple visible linear cracks across an asphalt road",
            "a network of narrow cracks spreading across a road surface",
            "long branching cracks splitting otherwise continuous roadway asphalt",
        ),
    ),
    VisionCategoryConfig(
        label="Road / Damaged Pavement",
        category="Road Damage",
        issue="Damaged Pavement",
        taxonomy_category="Road",
        taxonomy_issue="Damaged Pavement",
        prompts=(
            "a wide area of asphalt pavement with loose crumbling aggregate",
            "road pavement visibly raveling and eroded across a broad surface",
            "widespread uneven pavement with surface material worn away",
        ),
    ),
    VisionCategoryConfig(
        label="Road / Broken Footpath",
        category="Road Damage",
        issue="Broken Footpath",
        taxonomy_category="Road",
        taxonomy_issue="Broken Footpath",
        prompts=(
            "a broken pedestrian sidewalk",
            "a cracked damaged roadside footpath",
            "missing or uneven paving on a public footpath",
        ),
    ),
    VisionCategoryConfig(
        label="Garbage Accumulation",
        category="Waste Management",
        issue="Garbage Accumulation",
        taxonomy_category="Waste Management",
        taxonomy_issue="Garbage Accumulation",
        prompts=(
            "an accumulated pile of mixed everyday garbage on a public street",
            "many waste bags and loose household trash collected beside a road",
            "scattered and piled municipal waste covering a public area",
        ),
        automatic_resolution_supported=True,
    ),
    VisionCategoryConfig(
        label="Waste Management / Overflowing Bin",
        category="Waste Management",
        issue="Overflowing Bin",
        taxonomy_category="Waste Management",
        taxonomy_issue="Overflowing Bin",
        prompts=(
            "a public garbage bin overflowing with waste",
            "trash spilling out of a full municipal waste bin",
            "an overfilled outdoor rubbish container with garbage around it",
        ),
    ),
    VisionCategoryConfig(
        label="Waste Management / Illegal Dumping",
        category="Waste Management",
        issue="Illegal Dumping",
        taxonomy_category="Waste Management",
        taxonomy_issue="Illegal Dumping",
        prompts=(
            "bulky construction debris discarded on open public land",
            "large discarded furniture appliances and household items abandoned in a public area",
            "a heap of construction and household debris spread on bare public ground away from waste containers",
        ),
    ),
    VisionCategoryConfig(
        label="Water Leakage",
        category="Water Supply",
        issue="Water Leakage",
        taxonomy_category="Water",
        taxonomy_issue="Water Leakage",
        prompts=(
            "water leaking from a broken pipe",
            "a damaged water pipe leaking onto a street",
            "water flowing from a municipal pipe leak",
        ),
        automatic_resolution_supported=True,
    ),
    VisionCategoryConfig(
        label="Drainage Problem",
        category="Drainage",
        issue="Drainage Problem",
        taxonomy_category="Water",
        taxonomy_issue="Drainage Overflow",
        prompts=(
            "water or sewage visibly spilling beyond a roadside drain boundary onto the surrounding road or footpath",
            "wastewater emerging from a drain opening and flowing onto a street",
            "a drainage channel overflowing beyond its concrete walls onto an adjacent public surface",
        ),
        automatic_resolution_supported=True,
    ),
    VisionCategoryConfig(
        label="Water / Waterlogging",
        category="Drainage",
        issue="Waterlogging",
        taxonomy_category="Water",
        taxonomy_issue="Waterlogging",
        prompts=(
            "a street covered by stagnant accumulated water",
            "a broad shallow pool of standing water covering a roadway",
            "large areas of pooled stagnant water across a public street",
        ),
    ),
    VisionCategoryConfig(
        label="Water / Open Drain",
        category="Drainage",
        issue="Open Drain",
        taxonomy_category="Water",
        taxonomy_issue="Open Drain",
        prompts=(
            "a long uncovered roadside drainage channel with an exposed top and visible concrete interior",
            "an exposed concrete drain with visible channel walls and wastewater contained inside the channel",
            "an open drainage trench alongside a road or footpath with its channel interior visible",
        ),
    ),
    VisionCategoryConfig(
        label="Visible Streetlight Damage",
        category="Streetlight",
        issue="Visible Streetlight Damage",
        taxonomy_category="Infrastructure",
        taxonomy_issue="Broken Streetlight",
        prompts=(
            "a damaged streetlight",
            "a broken municipal street lamp",
            "a streetlight pole with visible damage",
        ),
        automatic_resolution_supported=True,
    ),
    VisionCategoryConfig(
        label="Infrastructure / Damaged Public Infrastructure",
        category="Other",
        issue="Damaged Public Infrastructure",
        taxonomy_category="Infrastructure",
        taxonomy_issue="Damaged Public Infrastructure",
        prompts=(
            "a visibly broken public railing or safety barrier",
            "a damaged municipal bench or public shelter",
            "a broken public structure requiring visible physical repair",
        ),
    ),
    VisionCategoryConfig(
        label="Infrastructure / Broken Traffic-related Infrastructure",
        category="Other",
        issue="Broken Traffic-related Infrastructure",
        taxonomy_category="Infrastructure",
        taxonomy_issue="Broken Traffic-related Infrastructure",
        prompts=(
            "a visibly damaged traffic sign or sign post",
            "a broken traffic signal structure",
            "a damaged road safety barrier or traffic control structure",
        ),
    ),
    VisionCategoryConfig(
        label="Control / No Civic Issue",
        category="Control / No Civic Issue",
        issue=None,
        taxonomy_category="Control / No Civic Issue",
        taxonomy_issue=None,
        prompts=(
            "a normal clean road",
            "an ordinary street scene",
            "a normal building",
            "a park or natural landscape",
        ),
        is_control=True,
    ),
)

VISION_LIMITATIONS: tuple[str, ...] = (
    "Zero-shot prompt classification is not a trained municipal defect detector.",
    "Scores are relative prompt-match scores, not calibrated probabilities.",
    "Current MVP analysis classifies the whole image and returns no bounding boxes.",
    "Nine expanded visual issue types still require representative real-image validation.",
    "Visually similar issue subclasses may be rejected by the conservative ambiguity gate.",
    "Streetlight inference addresses visible physical damage, not electrical operation.",
    "Resolution verification requires separate before-and-after analysis.",
    "Image similarity for Civic Issue Fusion is not implemented.",
)


def decode_uploaded_image(image_bytes: bytes, content_type: str | None) -> Image.Image:
    """Validate declared media, decoded format, dimensions, and pixel content."""

    normalized_content_type = (content_type or "").partition(";")[0].strip().casefold()
    declared_mime_type = IMAGE_MIME_ALIASES.get(
        normalized_content_type, normalized_content_type
    )
    if declared_mime_type not in SUPPORTED_IMAGE_FORMATS:
        raise UnsupportedImageMediaTypeError(
            "Supported image media types are image/jpeg, image/png, and image/webp."
        )
    if not image_bytes:
        raise InvalidImageError("The uploaded image is empty.")
    if len(image_bytes) > MAX_UPLOAD_BYTES:
        raise OversizedImageError(
            f"The uploaded image exceeds the {MAX_UPLOAD_MB} MB limit."
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(image_bytes)) as source:
                decoded_format = (source.format or "").upper()
                decoded_mime_type = DECODED_FORMAT_MIME_TYPES.get(decoded_format)
                width, height = source.size
                if decoded_mime_type is None:
                    raise UnsupportedImageMediaTypeError(
                        f"Decoded image format {decoded_format or 'unknown'} is unsupported."
                    )
                if decoded_mime_type != declared_mime_type:
                    raise UnsupportedImageMediaTypeError(
                        f"Declared image media type {declared_mime_type} does not match "
                        f"decoded image format {decoded_format} ({decoded_mime_type})."
                    )
                if width <= 0 or height <= 0 or width * height > MAX_IMAGE_PIXELS:
                    raise InvalidImageError("Image dimensions are invalid or too large.")
                source.verify()

            with Image.open(BytesIO(image_bytes)) as source:
                source.load()
                return ImageOps.exif_transpose(source).convert("RGB")
    except VisionInputError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        OSError,
        SyntaxError,
        UnidentifiedImageError,
    ) as exc:
        raise InvalidImageError("The uploaded file is corrupt or not a valid image.") from exc


class VisionAgent:
    """Apply civic prompt aggregation and conservative detection gates."""

    def __init__(self, provider: VisionProvider) -> None:
        self._provider = provider

    def analyze(self, image_bytes: bytes, content_type: str | None) -> VisionAnalysis:
        """Validate an image, score civic prompts, and return an explainable result."""

        image = decode_uploaded_image(image_bytes, content_type)
        prompt_entries = [
            (config, prompt)
            for config in VISION_CATEGORIES
            for prompt in config.prompts
        ]
        prompt_scores = self._provider.score_prompts(
            image, [prompt for _, prompt in prompt_entries]
        )
        if len(prompt_scores) != len(prompt_entries):
            raise VisionProviderError(
                "Vision provider returned a different number of scores than prompts."
            )
        if any(
            not math.isfinite(score) or score < 0.0 or score > 1.0
            for score in prompt_scores
        ):
            raise VisionProviderError("Vision provider returned an invalid prompt score.")

        category_scores: list[tuple[VisionCategoryConfig, float, str]] = []
        offset = 0
        for config in VISION_CATEGORIES:
            scores = prompt_scores[offset : offset + len(config.prompts)]
            offset += len(config.prompts)
            aggregate = sum(scores) / len(scores)
            top_index = max(range(len(scores)), key=scores.__getitem__)
            category_scores.append((config, aggregate, config.prompts[top_index]))

        category_scores.sort(key=lambda result: result[1], reverse=True)
        predictions = [
            VisionPrediction(
                category=config.category,
                issue=config.issue,
                taxonomy_category=config.taxonomy_category,
                taxonomy_issue=config.taxonomy_issue,
                relative_score=round(score, 6),
                top_prompt=top_prompt,
            )
            for config, score, top_prompt in category_scores
        ]

        civic_scores = [result for result in category_scores if not result[0].is_control]
        control_result = next(result for result in category_scores if result[0].is_control)
        top_civic = civic_scores[0]
        second_civic = civic_scores[1]
        control_margin = top_civic[1] - control_result[1]
        runner_up_margin = top_civic[1] - second_civic[1]
        detected = (
            top_civic[1] >= MIN_CIVIC_RELATIVE_SCORE
            and control_margin >= MIN_CONTROL_MARGIN
            and runner_up_margin >= MIN_RUNNER_UP_MARGIN
        )

        reasons = [
            f"Top civic relative score {top_civic[1]:.4f}; provisional minimum "
            f"{MIN_CIVIC_RELATIVE_SCORE:.2f}.",
            f"Margin over control {control_margin:.4f}; provisional minimum "
            f"{MIN_CONTROL_MARGIN:.2f}.",
            f"Margin over second civic category {runner_up_margin:.4f}; provisional "
            f"minimum {MIN_RUNNER_UP_MARGIN:.2f}.",
        ]
        if detected:
            reasons.append(
                "All provisional MVP detection gates passed; broader calibration is required."
            )
        else:
            failed_gates: list[str] = []
            if top_civic[1] < MIN_CIVIC_RELATIVE_SCORE:
                failed_gates.append("top civic score")
            if control_margin < MIN_CONTROL_MARGIN:
                failed_gates.append("control margin")
            if runner_up_margin < MIN_RUNNER_UP_MARGIN:
                failed_gates.append("runner-up margin")
            reasons.append(
                f"Detection rejected because these provisional gates failed: "
                f"{', '.join(failed_gates)}."
            )

        selected_config = top_civic[0] if detected else None
        return VisionAnalysis(
            detected=detected,
            category=selected_config.category if selected_config else None,
            issue=selected_config.issue if selected_config else None,
            taxonomy_category=(
                selected_config.taxonomy_category if selected_config else None
            ),
            taxonomy_issue=(selected_config.taxonomy_issue if selected_config else None),
            relative_score=round(top_civic[1], 6) if detected else None,
            provider=self._provider.provider_name,
            model=self._provider.model_id,
            device=self._provider.device,
            image_width=image.width,
            image_height=image.height,
            predictions=predictions,
            reasons=reasons,
            limitations=list(VISION_LIMITATIONS),
        )
