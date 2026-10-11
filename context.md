# Project Context: Smart Assistive Glasses

## 1. Project Overview

I am building a basic smart-assistance system for visually impaired people. It uses a camera feed, local object detection, and Google Gemini's vision API to provide spoken information about the surroundings.

**The main goal is to provide immediate alerts for nearby objects and hazards, along with richer scene descriptions, without allowing slower API responses to delay urgent alerts.**

Keep the implementation practical and understandable. I prefer Python and a modular codebase. Do not overengineer the project or implement features beyond the scope defined below.

## 2. Current Development Approach

For now, I have a **30-minute video recorded from a walking, first-person point of view on a footpath**. This video will be the initial input source.

However, the code must be designed so that switching from a video file to a live camera later requires minimal changes.

Create a common frame-input interface, such as:

- `VideoFileSource`: reads frames from the prerecorded video.
- `CameraSource`: a future implementation for live camera input.
- Both should provide frames to the same processing pipeline.

Preserve each frame's source timestamp or video timestamp. Do not rely only on processing time, because offline video processing speed may differ from real-time camera speed.

Start with the video file. Do not implement live-camera support until the video pipeline works.

## 3. Two Main Information Sources

The system has two sources of visual information.

### A. Local object detection using YOLO

YOLO runs locally on each processed frame and handles immediate object alerts.

Initially, use a lightweight pretrained model such as YOLOv8n, subject to compatibility and performance on my laptop.

The system should:

1. Read a frame from the video.
2. Run local object detection.
3. Identify relevant detected objects, such as people, cars, buses, and motorcycles.
4. Determine whether an object is inside a defined central region of the frame.
5. Consider the object's size and position in that region.
6. Trigger a short spoken alert when an object meets the configured alert conditions.

For example:

- A person enters the central region: "Person ahead."
- A vehicle occupies a significant part of the central region: "Vehicle ahead."

The central region should be configurable. Do not simply alert whenever an object appears anywhere in the frame.

Use normalized coordinates so the region works across different video resolutions. Make confidence thresholds, region boundaries, and object-size thresholds configurable.

Avoid repeating the same alert on every frame. Use a simple cooldown or event state so a continuously detected person does not cause endless repeated announcements. If practical, tracking can be added after basic detection works.

**Important limitation:** YOLO's general pretrained model does not automatically detect every hazard. In particular, it should not be assumed to reliably detect potholes, open drains, or all road-surface hazards without an appropriate model.

### B. Google Gemini vision API

Every five seconds during live assistance, capture a frame and send it to Google's Gemini vision API.

Use a configurable interval rather than hardcoding five seconds throughout the code.

Send the image with a custom prompt instructing Gemini to return structured information about the scene. The prompt should focus on information useful to a visually impaired pedestrian, including:

- Relevant objects and their positions.
- Potential hazards such as potholes, open drains, obstructions, and construction areas, when visible.
- Traffic-light state or displayed signals, when readable.
- Important environmental details that local object detection does not cover.
- The urgency or information level of each finding.
- A concise, natural-language description suitable for speech.

Require a structured JSON response. Define and validate a response schema rather than relying on arbitrary prose. Handle malformed JSON, missing fields, API errors, timeouts, and empty responses.

A possible response structure is:

{
  "scene_summary": "A short description of the scene",
  "observations": [
    {
      "description": "A potential hazard or relevant observation",
      "category": "hazard",
      "location": "center",
      "priority": "high",
      "confidence": 0.85,
      "speech_text": "Caution, a possible pothole is ahead"
    }
  ]
}

This is an illustrative schema, not a final mandatory schema. Improve it if needed, but keep it simple.

Treat the model's descriptions and confidence values as fallible. Do not present uncertain visual interpretations as guaranteed facts.

### API scheduling and latency

The Gemini request may take longer than the five-second interval. The local YOLO pipeline must not wait for the API to finish.

Use asynchronous or background processing so that:

- Local detection continues independently.
- API requests do not block frame processing or urgent alerts.
- Multiple slow requests do not accumulate without limit.
- A stale API response is not treated as a description of the current scene.
- Request errors do not stop local detection.

Start with one outstanding Gemini request at a time. If another scheduled request becomes due while the previous request is still running, skip the new request or use another explicitly documented bounded policy. Do not build an unlimited queue.

## 4. Speech and Alert Priorities

Both YOLO and Gemini can produce spoken information. They must share a central speech and alert manager.

The key rule is:

**An urgent local YOLO alert must not wait behind a Gemini scene description.**

For example, if Gemini is describing the surroundings and YOLO detects a person directly ahead, the system should interrupt the lower-priority speech and announce the immediate alert.

Use a simple priority system, such as:

- **Critical:** an immediate, high-confidence local hazard requiring interruption.
- **High:** an important potential hazard identified locally or by Gemini.
- **Normal:** useful scene information.
- **Low:** optional descriptive details.

The exact priority mapping should be configurable and documented. Do not classify every person or vehicle as critical solely because of its class. Consider its central position, bounding-box size, and other available evidence.

Gemini should also return an information or urgency rating. Map that rating to the application's priority system, but validate the returned value.

### Speech behavior

- Critical local alerts interrupt lower-priority speech.
- Important hazard announcements should take precedence over ordinary scene descriptions.
- Low-priority speech should be discarded or postponed when urgent alerts arrive.
- Duplicate alerts should be suppressed.
- Speech should remain short and useful while the person is walking.
- Avoid speaking every detected object or every Gemini observation.

Use a local text-to-speech solution initially, such as `pyttsx3` if it works reliably on the target operating system. Keep the speech implementation behind an interface so it can be replaced later.

Do not allow two independent speech components to speak simultaneously. Centralize speech scheduling, interruption, and prioritization.

## 5. Voice Commands and Scene Description

The user must be able to ask for a scene description by voice, including when continuous/live assistance is turned off.

For example, the user might say, "Describe the scene."

The system should capture a current frame, send it to Gemini, and speak the returned description.

While this description is being spoken:

- A critical local YOLO alert must interrupt it.
- A high-priority hazard identified by Gemini must also interrupt it when the result becomes available.
- Lower-priority scene information must not interrupt a more urgent alert.

If continuous assistance is off, the system should still support an on-demand description. The local detector should continue running in this mode only if that is part of the configured operating behavior. Do not silently assume it runs while everything is off.

For the first working version, voice input can be implemented after video processing, local alerts, Gemini integration, and speech prioritization work. A keyboard command can temporarily trigger scene description during development, but it is not a permanent replacement for the intended voice interaction.

## 6. Currency Recognition

Currency recognition for Indian notes and coins is a required feature of the intended basic system.

Explore Google's Teachable Machine for a suitable image-classification approach if it supports the required classes and deployment needs.

The currency component should identify supported Indian banknotes and coins from a camera image. Do not assume a model trained only on banknotes can recognize coins. The supported denominations, image capture method, and classification limitations must be explicit.

Keep currency recognition modular and separate from pedestrian hazard detection. It should be callable on demand and must not interfere with urgent safety alerts.

Do not start this feature before the video pipeline and local alert mechanism work. First verify whether a usable trained model and deployment path are available.

## 7. Proposed High-Level Architecture

Keep the project as one Python application with small, understandable modules. Avoid microservices and unnecessary infrastructure.

A possible structure is:

smart_assist/
    main.py
    config.py
    input/
        base.py
        video_source.py
        camera_source.py
    detection/
        yolo_detector.py
        spatial_rules.py
    scene/
        gemini_client.py
        scene_analyzer.py
        response_schema.py
    alerts/
        alert_manager.py
        speech_engine.py
        event_state.py
    voice/
        command_listener.py
    currency/
        currency_detector.py
    tests/
    outputs/
    README.md
    requirements.txt

This is a suggested structure, not a requirement to create all files immediately. Add modules only when they are needed.

The conceptual pipeline is:

Video or camera
    -> Frame input interface
    -> Local YOLO detection
    -> Spatial and object-size rules
    -> Local alert events
    -> Central priority and speech manager

In parallel:

Frame scheduler
    -> Gemini vision API
    -> JSON validation
    -> Scene observations and priority mapping
    -> Central priority and speech manager

On-demand commands:

Voice command
    -> Capture current frame
    -> Gemini scene description
    -> Central priority and speech manager

Currency recognition should be an independent feature integrated later.

## 8. Implementation Order

Implement and verify one small increment at a time. Do not generate the whole application at once.

### Phase 1: Video pipeline

- Open the 30-minute video using OpenCV. video is names as video.mp4
- Read frames and timestamps.
- Confirm frame count, dimensions, and video FPS.
- Save a short sample output or verify frames visually.
- Keep the input interface reusable for a future live camera.

### Phase 2: Local YOLO detection

- Load the lightweight pretrained model.
- Run inference on sampled frames.
- Draw bounding boxes, labels, and confidence values.
- Save an annotated output video and structured detection log.
- Record processing speed and any performance problems.

### Phase 3: Central-region rules

- Define a configurable central region.
- Filter relevant objects based on bounding-box position and size.
- Trigger basic alerts.
- Add cooldown or simple event state to prevent repeated speech.
- Test people and vehicles entering, remaining in, and leaving the region.

### Phase 4: Speech manager

- Add local text-to-speech.
- Route all announcements through one manager.
- Support interruption of lower-priority speech by critical alerts.
- Test duplicate suppression and priority ordering.

### Phase 5: Gemini integration

- Capture one frame every five seconds.
- Use a custom prompt and structured JSON response.
- Validate responses.
- Keep requests asynchronous and bounded.
- Route Gemini observations through the same alert manager.
- Verify that API delays and failures do not stop local detection.

### Phase 6: On-demand scene description

- Add a command to request a description of the current scene.
- First test using a keyboard command.
- Add voice input once the rest works.
- Verify that important hazards interrupt the spoken description.

### Phase 7: Currency recognition

- Evaluate Teachable Machine or another suitable lightweight classifier.
- Support the selected Indian currency classes.
- Test separately and integrate without affecting urgent alerts.

Do not move to the next phase until the current phase runs and its behavior has been verified. If time is limited, prioritize Phases 1 to 5.

## 9. Development Environment and Constraints

- I am developing on a low-end laptop.
- I will use VS Code with GitHub Copilot.
- I want to control the implementation and understand what is being built.
- Avoid expensive model training and unnecessary dependencies.
- Start with CPU-compatible inference and measure actual performance before considering optimizations.
- Do not assume a GPU is available.
- Keep API keys in environment variables or a local `.env` file excluded from Git.
- Do not upload the full 30-minute video to Gemini repeatedly. Send only the scheduled frames required by the application.
- Make video input the default development path.

## 10. How You Should Help Me

Work as a technical collaborator and tutor, not an autonomous coding agent.

For each step:

1. Explain the immediate goal in a few sentences.
2. Tell me which file or files need to be created or changed.
3. Give me one small task or a narrowly scoped Copilot prompt.
4. Explain the expected behavior and how to test it.
5. Wait for me to run it and report the result before moving forward.

When suggesting a Copilot prompt, explicitly instruct it to:

- Implement only the requested task.
- Avoid modifying unrelated files.
- Avoid implementing future phases.
- Explain the changes and relevant code.
- Include a simple verification procedure.
- Report assumptions and errors instead of silently working around them.

Do not make unnecessary architectural changes. Do not introduce databases, queues, cloud infrastructure, or complex tracking systems unless a demonstrated requirement justifies them.

If something fails, help me debug the actual error before adding more code. Do not replace the entire implementation just because one component has a problem.

## 11. Important Boundaries

- The project is an assistive prototype, not a certified safety device.
- Do not claim that generic YOLO detects potholes or every obstacle reliably.
- Do not treat Gemini's output as guaranteed correct or real-time.
- The five-second Gemini interval is a sampling interval, not a guarantee that results arrive every five seconds.
- Local detection and urgent alerts must remain independent of Gemini availability.
- Do not claim exact physical distance from bounding-box size alone.
- Do not implement features outside the scope above unless I explicitly request them.

## Immediate Next Task

Start with Phase 1. Help me inspect the video and build a minimal, reliable OpenCV video-input pipeline. Do not begin Gemini, speech, voice commands, currency recognition, or advanced tracking yet.