"""Local SigLIP provider and reusable Vision Agent construction."""

from functools import lru_cache
from threading import Lock
from typing import Any, Sequence

from PIL import Image

from app.agents.resolution_agent import ResolutionAgent
from app.agents.vision_agent import VisionAgent, VisionProviderError
from app.config import SIGLIP_MODEL_ID


class SigLIPVisionProvider:
    """Score civic prompts with one lazily loaded local SigLIP model."""

    def __init__(self, model_id: str = SIGLIP_MODEL_ID) -> None:
        self._model_id = model_id
        self._load_lock = Lock()
        self._inference_lock = Lock()
        self._model: Any | None = None
        self._processor: Any | None = None
        self._torch: Any | None = None
        self._device = "not_loaded"

    @property
    def provider_name(self) -> str:
        return "siglip_local"

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def device(self) -> str:
        return self._device

    def _ensure_loaded(self) -> None:
        """Load and cache the processor and model exactly once per provider."""

        if self._model is not None:
            return
        with self._load_lock:
            if self._model is not None:
                return
            try:
                import torch
                from transformers import AutoModel, AutoProcessor

                device = "cuda" if torch.cuda.is_available() else "cpu"
                processor = AutoProcessor.from_pretrained(self._model_id)
                model = AutoModel.from_pretrained(
                    self._model_id,
                    use_safetensors=True,
                )
                model.to(device)
                model.eval()
            except Exception as exc:
                raise VisionProviderError(
                    f"Unable to load local vision model {self._model_id}."
                ) from exc

            self._torch = torch
            self._processor = processor
            self._model = model
            self._device = device

    def score_prompts(
        self,
        image: Image.Image,
        prompts: Sequence[str],
    ) -> list[float]:
        """Return SigLIP sigmoid match scores in prompt order."""

        self._ensure_loaded()
        try:
            with self._inference_lock:
                inputs = self._processor(
                    text=list(prompts),
                    images=image,
                    padding="max_length",
                    return_tensors="pt",
                )
                inputs = {
                    name: value.to(self._device) for name, value in inputs.items()
                }
                with self._torch.inference_mode():
                    outputs = self._model(**inputs)
                    scores = self._torch.sigmoid(outputs.logits_per_image[0])
                return [float(score) for score in scores.cpu().tolist()]
        except VisionProviderError:
            raise
        except Exception as exc:
            raise VisionProviderError("Local SigLIP inference failed.") from exc


@lru_cache(maxsize=1)
def get_vision_provider() -> SigLIPVisionProvider:
    """Return the one process-local, lazily loaded SigLIP provider."""

    return SigLIPVisionProvider()


@lru_cache(maxsize=1)
def get_vision_agent() -> VisionAgent:
    """Return a classifier using the shared process-local provider."""

    return VisionAgent(get_vision_provider())


@lru_cache(maxsize=1)
def get_resolution_agent() -> ResolutionAgent:
    """Return a resolution verifier using the same process-local provider."""

    return ResolutionAgent(get_vision_provider())
