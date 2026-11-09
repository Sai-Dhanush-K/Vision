# Command reference

Run commands from the repository root after activating the virtual
environment. On Ubuntu:

```bash
source venv/bin/activate
```

On Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Use `python` below after activation. If the environment is not activated,
replace it with the full interpreter path:

- Ubuntu: `venv/bin/python`
- Windows: `venv\Scripts\python.exe`

## Setup and verification

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Ubuntu PyAudio prerequisite:

```bash
sudo apt update
sudo apt install portaudio19-dev python3-dev
python -m pip install --force-reinstall PyAudio
```

Run all automated tests:

```bash
python -m pytest -q
```

Show monitor options:

```bash
python -m smart_assist.detection.preview_player --help
```

## Phase 1: video input

Extract selected source frames and write `manifest.json` with source
timestamps:

```bash
python -m smart_assist.input.sample_frames \
  video.mp4 outputs/samples \
  --frame-index 0 \
  --frame-index 26450 \
  --frame-index 52899
```

Parameters:

- `video.mp4`: input video path.
- `outputs/samples`: output directory; generated files are Git-ignored.
- `--frame-index`: zero-based source frame to save. Repeat for multiple frames.

## Phase 2: YOLO detection

Run YOLO on selected frames:

```bash
python -m smart_assist.detection.annotate_samples \
  video.mp4 outputs/annotated \
  --frame-index 0 \
  --frame-index 26450 \
  --frame-index 52899
```

Outputs:

- Annotated JPEG frames.
- `outputs/annotated/detections.json`.

Create a bounded annotated MP4:

```bash
python -m smart_assist.detection.annotate_video \
  video.mp4 outputs/annotated.mp4 outputs/detections.json \
  --max-frames 30
```

The command writes bounding boxes, confidence labels, timing information, and
structured detections. `--max-frames` is required by the Python API and
defaults to 30 in the CLI.

## Phase 3: local threat monitor

Terminal-only monitor:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 20
```

The preview uses YOLO-World by default on this branch. YOLO-World supports
zero-shot labels such as trees and poles while reusing the existing central
geometry, tracking, cooldown, speech, and obstacle alert pipeline.

To explicitly use the original YOLOv8 detector:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --detector yolo --sample-fps 2 --max-frames 20
```

Add or replace the YOLO-World prompt labels by repeating `--world-label`:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 \
  --detector yolo-world \
  --world-label person \
  --world-label car \
  --world-label tree \
  --world-label pole \
  --max-frames 20
```

When custom labels are supplied, they replace the default YOLO-World label
set. Labels are zero-shot text prompts, not guaranteed classes; verify their
quality on the target video.

Parameters:

- `video.mp4`: input video.
- `--sample-fps 2`: source-video samples per second; this is not processing FPS.
- `--max-frames 20`: number of sampled frames to process.
- `--full-video`: ignore the frame limit and process until the source ends.
- `--display`: show the resized OpenCV preview.
- `--speech`: speak new local threat alerts with `pyttsx3`.
- `--detector`: choose `yolo-world` (default on this branch) or `yolo`.
- `--world-label`: add a custom YOLO-World prompt; repeat this option.

Run local detection with display and speech:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 --display --speech
```

The terminal prints frame index, source time, current threats, new alerts, and
processing time. Press `Q` or `Esc` in the preview to stop.

## Phase 4/5: optional Mistral assistance

Create `.env` in the repository root:

```env
MISTRAL_API_KEY=replace_with_your_key
```

Never put the real key in a command, source file, screenshot, or commit.

Enable periodic Mistral assistance:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 \
  --display --mistral-scene
```

Parameters:

- `--mistral-scene`: enables periodic Mistral scene analysis and speech.
- `--scene-interval 5`: source-video seconds between requests; default is 5.
- `--display`: shows the AI controls and video.
- `--speech`: enables local threat speech. Mistral mode initializes speech
  automatically so its results can be spoken.

Mistral periodic mode is intentionally short and navigation-focused. It uses
one outstanding request at a time; a slow request does not create an unlimited
queue or block YOLO.

## Phase 6: on-demand detailed scene description

Start the preview with Mistral enabled:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 \
  --display --mistral-scene
```

Use either:

- Click **Describe scene** in the preview.
- Press `S`.

This sends one frame using the detailed prompt and speaks an approximately
25–60 word scene description. It is different from the short periodic scan.
If another Mistral request is active, the on-demand request is skipped.

## Voice commands

Enable the microphone listener:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 \
  --display --mistral-scene --voice-commands
```

Supported detailed-summary commands:

- `Describe the scene`
- `Describe scene`
- `What is in front of me?`
- `What's in front of me?`
- `What is ahead of me?`
- `Describe my surroundings`

Supported periodic-AI commands:

- `Turn on advanced AI help`
- `Turn on advanced AI`
- `Enable advanced AI help`
- `Enable AI help`
- `Turn off advanced AI help`
- `Turn off advanced AI`
- `Disable advanced AI help`
- `Disable AI help`

Supported listening-mode commands:

- `Start listening`
- `Turn on voice commands`
- `Enable voice commands`
- `Stop listening`
- `Turn off voice commands`
- `Disable voice commands`

Voice command behavior:

- Voice commands are processed in a background listener.
- Recognition errors are printed as `voice_error=...`.
- Voice controls update the same state as the preview buttons.
- Turning advanced AI off pauses periodic Mistral scans but does not stop YOLO.
- Turning voice mode off ignores normal voice commands until voice listening is
  enabled again.

## Preview keyboard and mouse controls

- `A`: toggle periodic Mistral AI assistance.
- `S`: request a detailed scene description.
- `Q` or `Esc`: close the preview.
- Mouse click on **AI scan: ON/OFF**: same as `A`.
- Mouse click on **Describe scene**: same as `S`.

## Developer commands

Run only the speech-manager tests:

```bash
python -m pytest -q tests/test_speech_manager.py
```

Run scene and preview tests:

```bash
python -m pytest -q \
  tests/test_mistral_scene.py \
  tests/test_preview_player.py
```

Run voice parser tests:

```bash
python -m pytest -q tests/test_command_listener.py
```

Compile changed Python modules:

```bash
python -m py_compile \
  smart_assist/alerts/speech_manager.py \
  smart_assist/scene/mistral_scene.py \
  smart_assist/voice/command_listener.py \
  smart_assist/detection/preview_player.py
```

Check for whitespace errors:

```bash
git diff --check
```

## Important limitations

- YOLOv8n does not guarantee detection of potholes, open drains, or every
  obstacle.
- Mistral output can be wrong, delayed, stale, or incomplete.
- Bounding-box size is only a rough proximity signal, not exact distance.
- Speech recognition depends on microphone quality, noise, and network access.
- OpenCV windows require a working desktop GUI session.
- The current input is a prerecorded file; live camera support is not yet
  implemented.
- The system is a prototype and must not be treated as a certified safety
  system.
