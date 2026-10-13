import threading
import time

import numpy as np
import pytest

from smart_assist.scene.mistral_scene import (
    MistralSceneWorker,
    SceneAnalysisError,
    SceneObservation,
    SceneResult,
    _validate_result,
)


def test_scene_response_is_validated_and_normalized() -> None:
    result = _validate_result({
        "scene_summary": "Clear path with steps ahead",
        "observations": [{
            "description": "A curb crosses the path",
            "category": "hazard",
            "location": "center",
            "priority": "high",
            "confidence": 0.8,
            "speech_text": "Curb ahead, step carefully",
        }],
    })

    assert result == SceneResult(
        "Clear path with steps ahead",
        (SceneObservation(
            "A curb crosses the path",
            "hazard",
            "center",
            "high",
            0.8,
            "Curb ahead, step carefully",
        ),),
    )


def test_detailed_scene_summary_allows_about_fifty_words() -> None:
    summary = (
        "The walkway continues straight beside a quiet road. A low curb runs "
        "along the right edge, while the path appears open ahead. There is an "
        "entrance on the left and a possible change in pavement farther forward."
    )
    result = _validate_result(
        {"scene_summary": summary, "observations": []},
        detailed=True,
    )
    assert result.detailed
    assert 25 <= len(summary.split()) <= 60


def test_scene_response_rejects_invalid_priority() -> None:
    with pytest.raises(SceneAnalysisError, match="invalid observation"):
        _validate_result({
            "scene_summary": "A clear walking path",
            "observations": [{
                "description": "Unknown",
                "category": "hazard",
                "location": "center",
                "priority": "critical",
                "confidence": 0.8,
                "speech_text": "Unknown detail ahead",
            }],
        })


def test_worker_skips_submission_while_busy_and_reports_result() -> None:
    started = threading.Event()
    release = threading.Event()
    results: list[SceneResult] = []

    class SlowAnalyzer:
        def analyze(
            self, image: np.ndarray, detailed: bool = False
        ) -> SceneResult:
            started.set()
            release.wait(timeout=2)
            return SceneResult("Path is clear", (), detailed=detailed)

    worker = MistralSceneWorker(SlowAnalyzer(), results.append)
    try:
        image = np.zeros((10, 10, 3), dtype=np.uint8)
        assert worker.submit(image)
        assert started.wait(timeout=2)
        assert not worker.submit(image)
        release.set()
        deadline = time.time() + 2
        while time.time() < deadline and not results:
            time.sleep(0.01)
        assert results == [SceneResult("Path is clear", ())]
    finally:
        worker.close()
