# Project Progress Log

> This file is the current project-state record. Update it after every project-related chat exchange. Keep verified results separate from plans and user-reported outcomes.

## Current status

- **Project:** Smart Assistive Glasses prototype
- **Active phase:** Phase 3, central-region threat rules
- **Overall state:** Phase 1 and Phase 2 complete; Phase 3 geometry, proximity filtering, and cooldown events verified
- **Last updated:** 2026-10-12
- **Next permitted task:** Integrate threat candidates and event state into bounded video processing with structured alert events. Do not add speech yet.

## Phase checklist

- [x] **Phase 1: Video pipeline.** Inspect video metadata, read frames and source timestamps, verify dimensions/FPS/frame count/duration as available, and confirm sampled frames can be viewed or saved. Keep the input design reusable without implementing live-camera support.
- [ ] **Phase 2: Local YOLO detection.** Sampled inference, annotations, and structured logging verified; bounded annotated video processing remains.
- [ ] **Phase 3: Central-region rules and basic alert events.** Geometry, proximity filtering, and cooldown event emission verified; bounded pipeline integration remains.
- [ ] **Phase 4: Central speech manager and priority behavior.** Not started. Requires prior phases.
- [ ] **Phase 5: Bounded, asynchronous Gemini scene analysis.** Not started. Requires prior phases.
- [ ] **Phase 6: On-demand scene descriptions and voice input.** Not started. Requires prior phases.
- [ ] **Phase 7: Indian currency recognition.** Not started. Requires prerequisite verification and a separate model/deployment evaluation.

## Verified implementation

- **Input:** `/home/rguktrkvalley/Pictures/Vision/video.mp4` exists and is 897,576,633 bytes.
- **Environment:** The workspace uses `/home/rguktrkvalley/Pictures/Vision/venv/bin/python` (Python 3.10.12).
- **OpenCV:** `cv2` imported successfully; reported version `5.0.0`.
- **Video metadata:** OpenCV reported `29.97002997002997` FPS, `52,900` frames, `1920x1080` dimensions, and approximately `1,765.0967` seconds (`29.4183` minutes).
- **Frame reading:** Frames 0, 26,450, and 52,899 decoded successfully. Each had shape `(1080, 1920, 3)`, and OpenCV reported source timestamps of 0 ms, 882,548.33 ms, and 1,765,063.3 ms respectively.
- **Reusable pipeline:** `smart_assist.input.VideoFileSource` opens a video, exposes metadata, yields decoded frames with frame indices and OpenCV source timestamps, and releases resources through `close()` or a context manager.
- **Seeking and samples:** `VideoFileSource.seek()` positions the next read by zero-based frame index. `smart_assist.input.sample_frames` saves resized representative JPEGs and a timestamp manifest without adding generated output to Git.
- **Tests:** `tests/test_video_source.py` verifies metadata/frame decoding against `video.mp4` and rejects an unreadable path. `tests/test_sample_frames.py` verifies image and manifest output.
- **YOLO:** `smart_assist.detection.YoloDetector` loads the lightweight `yolov8n.pt` model, forces CPU inference, validates confidence configuration, and converts results into typed `Detection` records. Model weights remain local and ignored by Git.
- **Annotated samples:** `smart_assist.detection.annotate_samples` writes bounding boxes, labels, confidences, source timestamps, inference durations, and structured detections for selected frames.
- **Central threat rules:** `smart_assist.detection.spatial_rules` uses normalized configurable region bounds, relevant labels, minimum normalized box height, and minimum normalized box area. A detection must be relevant, centered, and large enough to pass both size thresholds.
- **Threat events:** `ThreatEventState` suppresses repeated alerts for a continuously present class, emits again after a configurable source-time cooldown, and emits again immediately after that class disappears and returns.

## Decisions and constraints

1. Use the prerecorded 30-minute walking POV video as the initial input. Live-camera support is future work and should require minimal changes to the pipeline.
2. Preserve source/video timestamps; offline processing time is not a substitute for the timestamp of the frame in the recording.
3. Keep the implementation in Python, modular but simple, and suitable for CPU-only development on a low-end laptop.
4. Work in small increments. Test, make targeted corrections, review the diff, update this log, and commit each completed increment when the required checks pass.
5. Do not start YOLO, Gemini, speech, voice commands, currency recognition, or advanced tracking before the video pipeline is verified.
6. A successful commit does not itself prove runtime correctness. Record test evidence separately.
7. The prototype is not a certified safety device. YOLO and Gemini outputs are fallible, and bounding-box size alone does not establish exact physical distance.

## Session history

### 2026-10-11: Project context and workflow files prepared

- **Change:** Created the project documentation set: `context.md`, `instructions.md`, `progress.md`, and `.github/copilot-instructions.md`.
- **Decision:** Use the existing project brief as the product/context reference and enforce one small implementation increment per development cycle.
- **Tests:** No application tests run. No repository implementation inspected as part of preparing these documentation files.
- **Status:** Documentation prepared; application progress remains unverified.
- **Next step:** In the AI IDE, inspect the repository and find the video file, then verify basic video metadata/frame reading as the first Phase 1 increment.

### 2026-10-12: Phase 1 video inspection verified

- **Change:** Inspected the repository state, located `video.mp4`, confirmed the workspace virtual environment, and verified OpenCV metadata and frame decoding at the beginning, midpoint, and end of the recording.
- **Tests:** Ran a focused Pylance Python snippet with the workspace interpreter. It exited with code 0 and decoded all three sampled frames successfully.
- **Decision:** Keep source timestamps from OpenCV for the reusable input module; do not substitute processing time. No later-phase feature work was started.
- **Status:** Verified input inspection; reusable video-source implementation remains planned.
- **Next step:** Implement only the small reusable video-file source module and test its frame/timestamp behavior.

### 2026-10-12: Manual setup of environment and dependencies
I manually created .gitignore and also pip installed
pip install opencv-python ultralytics google-genai pyttsx3 python-dotenv SpeechRecognition pytest
and created pip freeze requirements.txt file. I also created a .env file to store the API key for Google Gemini.

### 2026-10-12: Reusable video-file source implemented

- **Change:** Added `VideoFileSource`, `Frame`, and `VideoMetadata` under `smart_assist/input/`. The source reads sequentially, preserves OpenCV source timestamps, exposes basic metadata, and supports deterministic resource cleanup.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_video_source.py` passed: `2 passed in 1.03s`. Pylance syntax checks found no errors in the source or test file. The VS Code test tool did not discover the file, so the direct project-environment pytest command is the authoritative test result.
- **Decision:** Add only the file-based source now; live-camera support and all later processing features remain out of scope.
- **Status:** Verified reusable video-file source and focused tests.
- **Next step:** Add a small sample-frame verification/output step using this source, without adding detection or other later-phase features.

### 2026-10-12: Phase 1 sample output verified

- **Change:** Added `smart_assist.input.sample_frames`, a small command-line utility that seeks to selected source frames, writes resized JPEG samples, and records frame indices and source timestamps in `manifest.json`. Generated files are ignored under `outputs/`.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_video_source.py tests/test_sample_frames.py` passed: `3 passed in 28.94s`.
- **Verification command:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m smart_assist.input.sample_frames video.mp4 outputs/phase1_samples --frame-index 0 --frame-index 26450 --frame-index 52899` completed successfully. The three JPEGs were opened and visually inspected; the manifest preserved timestamps 0.0 ms, 882,548.33 ms, and 1,765,063.3 ms.
- **Status:** Phase 1 is verified and complete. No YOLO, Gemini, speech, voice, tracking, currency, or live-camera functionality was added.
- **Next step:** Begin Phase 2 with one small CPU-only YOLO model-loading/inference increment.

### 2026-10-12: Phase 2 YOLO inference verified

- **Change:** Added `smart_assist.detection.YoloDetector` and `Detection`. The detector runs Ultralytics YOLOv8n on CPU for one image and returns class IDs, labels, confidences, and bounding-box coordinates. Added focused tests for real video-frame inference and invalid confidence configuration.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_yolo_detector.py` passed: `2 passed in 60.22s`. The combined regression command `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_video_source.py tests/test_sample_frames.py tests/test_yolo_detector.py` passed: `5 passed in 10.36s`. Pylance reported no syntax errors in the detector.
- **Decision:** Use CPU explicitly and keep downloaded `*.pt` weights out of Git. This increment does not add alert rules, tracking, speech, or full-video inference.
- **Status:** Verified Phase 2 model loading and single-frame inference.
- **Next step:** Add annotated output and structured detection logging for selected sample frames.

### 2026-10-12: Phase 2 annotated samples and detection log verified

- **Change:** Added `smart_assist.detection.annotate_samples`, which runs the CPU detector on selected source frames, draws bounding boxes/labels/confidences, and writes `detections.json` with source timestamps and inference timing. Added a focused test.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_annotate_samples.py` passed: `1 passed in 12.28s`.
- **Verification command:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m smart_assist.detection.annotate_samples video.mp4 outputs/phase2_samples --frame-index 0 --frame-index 26450 --frame-index 52899` completed successfully. All three annotated images and the JSON log were opened/inspected.
- **Observed performance:** Inference took approximately 4,275 ms, 317 ms, and 542 ms for the start, midpoint, and final 1920x1080 frames respectively on CPU. The first run includes model/runtime warm-up and is not treated as steady-state FPS.
- **Status:** Verified sampled annotation and structured logging. No alert rules, tracking, speech, Gemini, currency, or live-camera functionality was added.
- **Next step:** Add bounded annotated video processing and performance measurement, then review whether Phase 2 is complete.

### 2026-10-12: Phase 2 bounded annotated video verified

- **Change:** Added `smart_assist.detection.annotate_video`, which writes a bounded MP4 preview, draws YOLO annotations, preserves source timestamps in a JSON log, and records per-frame and summary inference timing.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_annotate_video.py` passed: `1 passed in 5.82s`.
- **Verification command:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m smart_assist.detection.annotate_video video.mp4 outputs/phase2_preview.mp4 outputs/phase2_video_log.json --max-frames 5` processed 5 real frames successfully. Source FPS was 29.9700; average inference was 985.94 ms, minimum 310.49 ms, and maximum 3417.60 ms.
- **Decision:** Keep video processing explicitly bounded with `--max-frames`; processing the complete 30-minute recording on this CPU is not silently started.
- **Status:** Phase 2 checklist is verified for model loading, sampled inference, annotation, structured logging, and measured bounded video output. No alert rules, tracking, speech, Gemini, currency, or live-camera functionality was added.
- **Next step:** Begin Phase 3 with a configurable central-region geometry helper and focused tests; do not add speech or alert cooldown behavior yet.

### 2026-10-12: Phase 3 central threat geometry verified

- **Change:** Added `NormalizedRegion`, `ThreatRuleConfig`, `ThreatCandidate`, and `find_threats` in `smart_assist.detection.spatial_rules`. Human/vehicle labels are configurable, region bounds are normalized, and both box height and box area thresholds reject small distant detections even when centered.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_spatial_rules.py` passed: `6 passed in 3.47s`. The full Phase 1/2 regression suite remains covered by the prior `7 passed` result.
- **Real-frame verification:** On frames 0, 26,450, and 52,899, the rules returned one large central `person` threat at frame 0, no threat for the detected car at frame 26,450 because it was outside/too small for the configured central proximity rule, and no threats at frame 52,899.
- **Decision:** Keep this layer independent from speech. It produces typed threat candidates; event cooldown and alert delivery are the next Phase 3 increment.
- **Status:** Phase 3 central geometry and proximity filtering verified. No speech, tracking, Gemini, currency, or live-camera functionality was added.
- **Next step:** Add event-state/cooldown handling for repeated central threats.

### 2026-10-12: Phase 3 threat event cooldown verified

- **Change:** Added `ThreatEventState` and `ThreatAlert` in `smart_assist.detection.threat_events`. Events are keyed by class label, use source timestamps, suppress continuous duplicates, re-alert after a configurable cooldown, and re-alert when a threat disappears and returns.
- **Tests:** `/home/rguktrkvalley/Pictures/Vision/venv/bin/python -m pytest -q tests/test_threat_events.py tests/test_spatial_rules.py` passed: `11 passed in 3.76s`.
- **Decision:** Keep event state independent from speech and tracking. The event layer emits structured messages such as `Person ahead.` but does not speak them.
- **Status:** Phase 3 geometry, proximity filtering, and cooldown behavior verified. No speech, tracking, Gemini, currency, or live-camera functionality was added.
- **Next step:** Integrate threat candidates and event state into bounded video processing with structured alert events.
