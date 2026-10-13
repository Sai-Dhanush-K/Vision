"""Bounded Mistral vision analysis for optional scene guidance."""

from base64 import b64encode
from dataclasses import dataclass
import json
import os
from pathlib import Path
import threading
from typing import Any, Callable, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

import cv2
import numpy as np
from dotenv import load_dotenv


class SceneAnalysisError(RuntimeError):
    """Raised when Mistral returns an unusable scene response."""


@dataclass(frozen=True)
class SceneObservation:
    """One concise, non-local-detection observation."""

    description: str
    category: str
    location: str
    priority: str
    confidence: float
    speech_text: str


@dataclass(frozen=True)
class SceneResult:
    """Validated response from the Mistral scene prompt."""

    scene_summary: str
    observations: tuple[SceneObservation, ...]
    detailed: bool = False


class SceneAnalyzer(Protocol):
    """Analyzer contract used by the bounded background worker."""

    def analyze(self, image: np.ndarray, detailed: bool = False) -> SceneResult:
        """Analyze one BGR frame."""


DEFAULT_PROMPT = """
You are a conservative navigation assistant for a blind pedestrian walking forward.

Your task is NOT to describe the entire image. Identify only one highly useful
navigation-related observation that local object detection does not cover.

CONTEXT:
- This image was captured approximately 5 seconds before the result may be used.
- The pedestrian may have moved past objects visible in this frame.
- You do not know the pedestrian's exact current position, speed, or distance
  from an object.
- Prefer stable features farther ahead that could affect the walking route.
- Never claim that an object is currently nearby or that a hazard is certain
  based only on this delayed image.

REPORT AN OBSERVATION ONLY IF:
1. It is clearly visible and reasonably certain.
2. It is relevant to the pedestrian's forward walking route.
3. It provides useful information not covered by local YOLO detection.
4. It could change a navigation decision or help the pedestrian prepare ahead.
5. It is still likely to be useful despite the image delay.

PRIORITIZE:
- Steps, stairs, curbs, or significant changes in walkway level.
- An obstructed, blocked, or closed footpath that may require a route change.
- Construction or barriers that significantly affect the walking route.
- Clearly visible entrances or route changes when they are relevant to navigation.
- Other clearly identifiable, important walking-surface hazards.

DO NOT:
- Describe the entire scene or list all visible objects.
- Report people, cars, buses, bicycles, motorcycles, or generic objects as threats.
- Report an object merely because it is visible or far away.
- Speculate about potholes, steps, obstacles, or route conditions that are unclear.
- Give traffic-signal states or other rapidly changing information as current
  based on this delayed frame.
- Repeat minor details, generic surroundings, or information with no clear
  navigation benefit.
- Invent distances, directions, or certainty that the image does not establish.

OUTPUT RULES:
- Return valid JSON only, using exactly the required structure below.
- Use Simple Wording: Use concise, clear, and simple language in all fields. 
- Return ZERO or ONE observation. Choose only the single most useful observation.
- Use an empty observations list whenever no observation meets all the criteria.
- Do not add alternative observations just to fill the response.
- scene_summary must contain 5 to 10 words. If nothing useful is visible, use:
  "No important navigation change visible."
- speech_text must contain AT MOST 5 words, using concise natural language.
- Use priority "high" only for a clearly visible, important navigation issue.
  Otherwise use "normal" or "low" as appropriate.
- Confidence must be between 0 and 1. Do not use high confidence for guesses.

Required JSON structure:
{
  "scene_summary": "5 to 10 words",
  "observations": [
    {
      "description": "One concise, useful detail",
      "category": "hazard|navigation|signal|environment",
      "location": "left|center|right|near|far",
      "priority": "high|normal|low",
      "confidence": 0.0,
      "speech_text": "At most five words"
    }
  ]
} 
"""

DETAILED_PROMPT = """
You are a patient scene-description assistant for a blind pedestrian.
Describe the current image in useful, concrete language for navigation.
Return JSON only with exactly this structure:
{"scene_summary":"a spoken description of about 40 to 60 words",
 "observations":[]}

The scene_summary should mention the visible walking path, important surroundings,
surface or route changes, signs or entrances that can be read, and the relative
position of useful landmarks. Do not invent details, exact distances, or certainty.
Do not focus on people or vehicles because local detection already reports them.
Use simple natural sentences. Keep it between 25 and 60 words.
Use an empty observations list; this request is for the detailed summary only.
"""


def _word_count(text: str) -> int:
    return len(text.split())


def _validate_result(payload: Any, detailed: bool = False) -> SceneResult:
    if not isinstance(payload, dict):
        raise SceneAnalysisError("Mistral response must be a JSON object")
    summary = payload.get("scene_summary")
    observations = payload.get("observations")
    if (
        not isinstance(summary, str)
        or not (
            25 <= _word_count(summary) <= 60
            if detailed
            else 1 <= _word_count(summary) <= 12
        )
        or not isinstance(observations, list)
    ):
        raise SceneAnalysisError("Mistral response has an invalid scene summary")

    validated: list[SceneObservation] = []
    for item in observations:
        if not isinstance(item, dict):
            raise SceneAnalysisError("scene observation must be an object")
        values = [item.get(field) for field in (
            "description", "category", "location", "priority", "speech_text"
        )]
        description, category, location, priority, speech_text = values
        confidence = item.get("confidence")
        if (
            not all(isinstance(value, str) and value.strip() for value in values)
            or location not in {"left", "center", "right", "near", "far"}
            or priority not in {"high", "normal", "low"}
            or not isinstance(confidence, (int, float))
            or not 0 <= confidence <= 1
            or not 1 <= _word_count(speech_text) <= 12
        ):
            raise SceneAnalysisError("Mistral response has an invalid observation")
        validated.append(
            SceneObservation(
                description=description,
                category=category,
                location=location,
                priority=priority,
                confidence=float(confidence),
                speech_text=speech_text,
            )
        )
    return SceneResult(summary, tuple(validated), detailed=detailed)


class MistralSceneAnalyzer:
    """Call Mistral's vision chat endpoint for one frame at a time."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "pixtral-12b-2409",
        timeout_seconds: float = 15.0,
        prompt: str = DEFAULT_PROMPT,
    ) -> None:
        load_dotenv()
        self.api_key = api_key or os.getenv("MISTRAL_API_KEY")
        if not self.api_key:
            raise ValueError("MISTRAL_API_KEY is not configured")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.prompt = prompt

    def analyze(self, image: np.ndarray, detailed: bool = False) -> SceneResult:
        if image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("image must have shape (height, width, 3)")
        encoded_ok, encoded = cv2.imencode(
            ".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80]
        )
        if not encoded_ok:
            raise SceneAnalysisError("could not encode frame as JPEG")
        image_data = b64encode(encoded.tobytes()).decode("ascii")
        body = json.dumps({
            "model": self.model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": DETAILED_PROMPT if detailed else self.prompt,
                    },
                    {"type": "image_url", "image_url": {
                        "url": f"data:image/jpeg;base64,{image_data}"
                    }},
                ],
            }],
        }).encode("utf-8")
        http_request = urllib_request.Request(
            "https://api.mistral.ai/v1/chat/completions",
            data=body,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib_request.urlopen(
                http_request, timeout=self.timeout_seconds
            ) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (urllib_error.URLError, TimeoutError, OSError) as error:
            raise SceneAnalysisError("Mistral request failed") from error
        try:
            content = result["choices"][0]["message"]["content"]
            payload = json.loads(content) if isinstance(content, str) else content
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise SceneAnalysisError("Mistral returned invalid JSON content") from error
        return _validate_result(payload, detailed=detailed)


class MistralSceneWorker:
    """Run at most one scene request in the background."""

    def __init__(
        self,
        analyzer: SceneAnalyzer,
        on_result: Callable[[SceneResult], None],
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        self._analyzer = analyzer
        self._on_result = on_result
        self._on_error = on_error
        self._condition = threading.Condition()
        self._pending: tuple[np.ndarray, bool] | None = None
        self._closed = False
        self._busy = False
        self._thread = threading.Thread(
            target=self._run, name="mistral-scene-worker", daemon=True
        )
        self._thread.start()

    def submit(self, image: np.ndarray, detailed: bool = False) -> bool:
        """Submit a frame, returning false when a request is already running."""

        with self._condition:
            if self._closed:
                raise RuntimeError("Mistral scene worker is closed")
            if self._busy or self._pending is not None:
                return False
            self._pending = (image.copy(), detailed)
            self._condition.notify()
            return True

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while True:
            with self._condition:
                while self._pending is None and not self._closed:
                    self._condition.wait()
                if self._closed and self._pending is None:
                    return
                image, detailed = self._pending
                self._pending = None
                self._busy = True
            try:
                self._on_result(self._analyzer.analyze(image, detailed=detailed))
            except Exception as error:
                if self._on_error is not None:
                    self._on_error(error)
            finally:
                with self._condition:
                    self._busy = False
