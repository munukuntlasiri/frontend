"""Run a local SigLIP zero-shot inference smoke test on a real image."""

import argparse
from pathlib import Path
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents.vision_agent import VISION_CATEGORIES
from app.config import SIGLIP_MODEL_ID

MODEL_ID = SIGLIP_MODEL_ID
PROMPT_GROUPS: dict[str, tuple[str, ...]] = {
    (
        config.taxonomy_category
        if config.taxonomy_issue is None
        else f"{config.taxonomy_category} / {config.taxonomy_issue}"
    ): config.prompts
    for config in VISION_CATEGORIES
}


def parse_args() -> argparse.Namespace:
    """Read the required image path from the command line."""

    parser = argparse.ArgumentParser(
        description="Test local SigLIP inference with CivicResolve prompt groups."
    )
    parser.add_argument("image", type=Path, help="Path to a real image file")
    return parser.parse_args()


def import_dependencies() -> dict[str, Any]:
    """Import and return every dependency required by this smoke test."""

    try:
        import PIL
        from PIL import Image, ImageOps, UnidentifiedImageError
        import safetensors
        import sentencepiece
        import torch
        import torchvision
        import transformers
    except ImportError as exc:
        raise RuntimeError(
            "A vision dependency is missing. Install requirements.txt in the active "
            f"virtual environment. Original error: {exc}"
        ) from exc

    return {
        "PIL": PIL,
        "Image": Image,
        "ImageOps": ImageOps,
        "UnidentifiedImageError": UnidentifiedImageError,
        "safetensors": safetensors,
        "sentencepiece": sentencepiece,
        "torch": torch,
        "torchvision": torchvision,
        "transformers": transformers,
    }


def decode_image(image_path: Path, dependencies: dict[str, Any]) -> Any:
    """Validate that an image exists and can be decoded as RGB pixels."""

    resolved_path = image_path.expanduser().resolve()
    if not resolved_path.is_file():
        raise ValueError(f"Image file does not exist: {resolved_path}")

    image_module = dependencies["Image"]
    image_ops = dependencies["ImageOps"]
    unidentified_error = dependencies["UnidentifiedImageError"]
    try:
        with image_module.open(resolved_path) as source_image:
            source_image.load()
            image = image_ops.exif_transpose(source_image).convert("RGB")
    except (unidentified_error, OSError) as exc:
        raise ValueError(f"Image could not be decoded: {resolved_path}") from exc

    print(f"Image: {resolved_path}")
    print(f"Decoded image size: {image.width}x{image.height}")
    return image


def flatten_prompts() -> tuple[list[str], list[tuple[str, str]]]:
    """Flatten configured groups while retaining each prompt's category."""

    prompts: list[str] = []
    prompt_metadata: list[tuple[str, str]] = []
    for category, category_prompts in PROMPT_GROUPS.items():
        for prompt in category_prompts:
            prompts.append(prompt)
            prompt_metadata.append((category, prompt))
    return prompts, prompt_metadata


def run_inference(
    image: Any,
    dependencies: dict[str, Any],
) -> list[tuple[str, float, str]]:
    """Load SigLIP lazily and average its prompt scores within each category."""

    torch = dependencies["torch"]
    transformers = dependencies["transformers"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Inference device: {device}")
    print(f"Loading model: {MODEL_ID}")

    processor = transformers.AutoProcessor.from_pretrained(MODEL_ID)
    model = transformers.AutoModel.from_pretrained(
        MODEL_ID,
        use_safetensors=True,
    )
    model.to(device)
    model.eval()

    prompts, prompt_metadata = flatten_prompts()
    inputs = processor(
        text=prompts,
        images=image,
        padding="max_length",
        return_tensors="pt",
    )
    inputs = {name: value.to(device) for name, value in inputs.items()}

    with torch.inference_mode():
        outputs = model(**inputs)
        prompt_scores = torch.sigmoid(outputs.logits_per_image[0]).cpu().tolist()

    grouped_scores: dict[str, list[tuple[float, str]]] = {
        category: [] for category in PROMPT_GROUPS
    }
    for score, (category, prompt) in zip(
        prompt_scores, prompt_metadata, strict=True
    ):
        grouped_scores[category].append((float(score), prompt))

    results: list[tuple[str, float, str]] = []
    for category, scores_and_prompts in grouped_scores.items():
        aggregate = sum(score for score, _ in scores_and_prompts) / len(
            scores_and_prompts
        )
        _, top_prompt = max(scores_and_prompts, key=lambda item: item[0])
        results.append((category, aggregate, top_prompt))
    return sorted(results, key=lambda item: item[1], reverse=True)


def print_results(results: list[tuple[str, float, str]]) -> None:
    """Print ranked relative scores without presenting them as probabilities."""

    print("\nResults: relative zero-shot prompt scores")
    print(
        "Aggregation: arithmetic mean of SigLIP sigmoid match scores for all "
        "prompts in each category."
    )
    for category, score, top_prompt in results:
        print(f"\nCategory: {category}")
        print(f"Aggregated relative score: {score:.4f}")
        print(f"Top matching prompt: {top_prompt}")

    top_category, top_score, _ = results[0]
    print(f"\nTop overall category: {top_category} ({top_score:.4f})")
    print(
        "Streetlight prompts assess visible physical damage only, not electrical function."
    )
    print("No production detection or rejection threshold has been applied.")


def main() -> int:
    """Validate the environment and execute one real-image inference."""

    print(f"Python version: {sys.version.split()[0]}")
    try:
        dependencies = import_dependencies()
        print("Vision dependency imports: OK")
        print(f"PyTorch version: {dependencies['torch'].__version__}")
        print(f"Torchvision version: {dependencies['torchvision'].__version__}")
        print(f"Transformers version: {dependencies['transformers'].__version__}")
        print(f"Pillow version: {dependencies['PIL'].__version__}")
        print(f"CUDA available: {dependencies['torch'].cuda.is_available()}")

        args = parse_args()
        image = decode_image(args.image, dependencies)
        results = run_inference(image, dependencies)
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        return 1

    print_results(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
