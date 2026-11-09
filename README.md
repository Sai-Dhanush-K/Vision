# Smart Assistive Glasses Prototype

A CPU-friendly Python prototype for a walking point-of-view video. The project
combines:

- Local YOLO-World object detection for immediate person, vehicle, obstacle,
  tree, pole, and other configured zero-shot-label alerts.
- Configurable central/lower-frame geometry so distant or side objects do not
  automatically become threats.
- Lightweight tracking and cooldown state so the same tracked object is not
  announced on every sampled frame.
- Optional local speech through `pyttsx3`.
- Optional Mistral vision analysis for short, non-local navigation guidance.
- On-demand detailed scene descriptions of approximately 25–60 words.
- Optional voice commands for scene descriptions and AI-assistance controls.
- An optional OpenCV preview with mouse and keyboard controls.

This is an experimental assistive prototype, not a certified safety device.
YOLO and Mistral can miss objects, misunderstand scenes, or return stale and
uncertain information. Do not rely on it as the only source of safety-critical
navigation.

## Current status

The current development input is `video.mp4`, a prerecorded walking video.
Live-camera support is not implemented yet.

The default local monitor samples the source video at approximately two frames
per second. Mistral scene assistance is optional and, when enabled, schedules
one frame approximately every five source-video seconds. Mistral requests run
in the background and do not block local YOLO detection.

## Project layout

```text
smart_assist/
  alerts/
    speech_manager.py       Priority speech queue and pyttsx3 adapter
  detection/
    yolo_detector.py        CPU YOLOv8 inference
    yolo_world_detector.py  CPU YOLO-World zero-shot inference
    spatial_rules.py        Central/lower geometry and classifications
    tracker.py              Lightweight IoU tracking
    threat_events.py        Per-track cooldown and alert events
    preview_player.py       Terminal monitor, optional video UI and controls
  input/
    video_source.py         Reusable OpenCV video-file source
    sample_frames.py        Representative frame extraction
  scene/
    mistral_scene.py        Mistral client, JSON validation and worker
  voice/
    command_listener.py     Optional microphone command listener
tests/                      Automated tests
video.mp4                   Local input video; ignored by Git
commands.md                Command reference
```

Generated media and model weights are ignored by Git. The YOLO weights file
`yolov8n.pt` is downloaded locally when needed.
On this branch, the preview defaults to `yolov8s-world.pt`; this weight file is
also downloaded locally when first used.

## Requirements

- Python 3.10 or newer is recommended.
- A CPU is supported; a GPU is not required.
- OpenCV must be able to open the video file.
- Local speech requires a working system speech backend.
- Voice commands require a microphone and the `SpeechRecognition` dependency.
- Mistral assistance requires an internet connection and a Mistral API key.
- A desktop session is required for `--display`.

## Ubuntu setup

Open a terminal in the repository:

```bash
cd /path/to/Vision
```

Install Python and the system packages needed by OpenCV, microphone input,
and PyAudio:

```bash
sudo apt update
sudo apt install python3 python3-venv python3-dev portaudio19-dev
```

`portaudio19-dev` and `python3-dev` are important for PyAudio. If installation
fails with:

```text
fatal error: portaudio.h: No such file or directory
```

install the missing development headers:

```bash
sudo apt update
sudo apt install portaudio19-dev python3-dev
```

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If the project directory already contains `venv`, activate it instead of
creating another environment:

```bash
source venv/bin/activate
```

If PyAudio was attempted before the PortAudio packages were installed, retry:

```bash
python -m pip install --force-reinstall PyAudio
```

## Windows setup

Install Python 3.10 or newer from [python.org](https://www.python.org/) and
make sure **Add Python to PATH** is selected. Then open PowerShell in the
repository:

```powershell
cd C:\path\to\Vision
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell blocks activation for the current user, run PowerShell once as
your normal user:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\venv\Scripts\Activate.ps1
```

PyAudio normally installs from a Windows wheel. If no compatible wheel is
available for the selected Python version, use a supported Python version or
install a matching PyAudio wheel before enabling voice commands. The local
YOLO and preview features do not require a microphone.

## Environment variables

Create a local `.env` file in the repository root. It is ignored by Git.

```env
MISTRAL_API_KEY=replace_with_your_mistral_key
```

Never commit or paste the real key into source code, issue reports, terminal
logs, or chat. Mistral is only initialized when `--mistral-scene` is used.

## First verification

Activate the virtual environment, then run:

```bash
python -m pytest -q
```

The suite covers video input, detection, spatial rules, tracking, speech
scheduling, Mistral validation, preview controls, and voice-command parsing.

Check the available monitor options:

```bash
python -m smart_assist.detection.preview_player --help
```

## Typical runs

Terminal-only local detection, 20 sampled frames:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 20
```

The preview defaults to YOLO-World on the `test-yolo-world` branch. Use
`--detector yolo` to select the original YOLOv8 detector. YOLO-World labels
are configurable with repeated `--world-label` options, for example:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --detector yolo-world \
  --world-label person --world-label car \
  --world-label tree --world-label pole
```

YOLO-World is zero-shot, but its detections are still fallible. A label such as
`tree` or `pole` can be passed into the same central/lower geometry and
cooldown pipeline; it is not a guarantee that every tree or pole is detected.

Local detection with terminal output, video preview, and speech:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 20 --display --speech
```

Mistral periodic assistance with speech and preview controls:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 \
  --display --mistral-scene
```

Mistral periodic assistance plus microphone voice commands:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 100 \
  --display --mistral-scene --voice-commands
```

Use `--full-video` instead of `--max-frames 100` to process sampled frames
until the source video ends. This can take a long time on a CPU.

## Preview controls

When `--display` is enabled, the preview shows two controls:

1. **AI scan: ON/OFF**
   - Mouse click or `A` key.
   - Pauses or resumes scheduled Mistral assistance.
   - Does not stop local YOLO detection or local threat alerts.
2. **Describe scene**
   - Mouse click or `S` key.
   - Requests one detailed 25–60 word Mistral description.
   - The request is skipped if another Mistral request is already running.

Press `Q` or `Esc` to close the preview.

## Voice commands

Voice commands are optional and require `--voice-commands`.

Detailed on-demand scene description:

- “Describe the scene”
- “What is in front of me?”
- “What is ahead of me?”
- “Describe my surroundings”

Periodic advanced AI assistance:

- “Turn on advanced AI help”
- “Turn off advanced AI help”
- “Enable AI help”
- “Disable AI help”

Voice-listening mode:

- “Start listening”
- “Stop listening”
- “Turn on voice commands”
- “Turn off voice commands”

Recognition uses the configured `SpeechRecognition` backend and may be
unreliable because of microphone quality, background noise, network access, or
accent recognition. Local threat detection continues if recognition fails.

## Alert behavior

The local pipeline uses these defaults:

- Sampling: 2 source frames per second.
- Threat region: central 20% of the image horizontally and lower half
  vertically.
- Minimum object width: 10% of frame width.
- Minimum object height: 15% of frame height.
- Minimum object area: 2% of frame area.
- Local event cooldown: 5 seconds.
- Tracking gap: 10 seconds.

People produce `Person ahead.` Vehicles produce `Vehicle ahead.` Other
detections that pass the configured geometry can produce `Obstacle ahead.`.
Generic YOLO does not reliably detect potholes, open drains, or every surface
hazard.

## Mistral behavior and limitations

Periodic assistance uses a short navigation prompt and returns a compact JSON
response. It intentionally avoids repeating people and vehicles already
handled by local YOLO.

On-demand descriptions use a different prompt and request approximately
25–60 words for a broader explanation of the visible path and surroundings.

Only one Mistral request is allowed at a time. If the previous request is
still running, a scheduled request is skipped. API errors are printed and do
not stop local processing. Mistral output is fallible and may describe a frame
that is already several seconds old.

## Troubleshooting

### PyAudio cannot find `portaudio.h` on Ubuntu

Install the development headers and retry:

```bash
sudo apt update
sudo apt install portaudio19-dev python3-dev
python -m pip install --force-reinstall PyAudio
```

### No preview window appears

Use terminal mode first. OpenCV GUI support depends on the desktop session,
Wayland/X11 configuration, and installed GUI libraries:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 20
```

### No sound

Check the operating-system output device and test without Mistral first:

```bash
python -m smart_assist.detection.preview_player \
  video.mp4 --sample-fps 2 --max-frames 20 --speech
```

### Voice commands do not respond

Confirm that a microphone is visible to the operating system, install PyAudio,
reduce background noise, and run with `--voice-commands`. The terminal prints
`voice_error=...` when microphone initialization fails.

### Mistral errors

Confirm that `.env` contains `MISTRAL_API_KEY`, the key is valid, the account
can access the configured model, and the machine has internet access. Do not
print the key while debugging.

## Development notes

- Keep source timestamps from the input video; processing time is not a source
  timestamp.
- Do not upload the complete 30-minute video. Only scheduled individual frames
  are sent to Mistral.
- Keep local urgent alerts independent from Mistral latency or failure.
- Do not commit `.env`, `video.mp4`, model weights, generated outputs, or
  Python cache files.
- Make focused changes and run the relevant tests before committing.
