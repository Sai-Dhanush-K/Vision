
# commands for output of phase 3 without display
/home/rguktrkvalley/Pictures/Vision/venv/bin/python   -m smart_assist.detection.preview_player   video.mp4   --sample-fps 2   --max-frames 20

# commands for output of phase 3 with display

  /home/rguktrkvalley/Pictures/Vision/venv/bin/python   -m smart_assist.detection.preview_player   video.mp4   --sample-fps 2   --max-frames 20   --display
# comm
  /home/rguktrkvalley/Pictures/Vision/venv/bin/python   -m smart_assist.detection.preview_player   video.mp4   --sample-fps 2   --full-video   --display

# optional Mistral scene guidance with video and speech
# --mistral-scene enables the five-second background scene scan.
# --speech enables local threat speech; --mistral-scene also initializes speech
# so Mistral observations can be spoken.
# --display shows the two on-screen controls:
#   AI scan: ON/OFF (click or press A)
#   Describe scene (click or press S) requests a detailed 25-60 word summary.
# The AI scan button pauses/resumes scheduled Mistral requests. The scene button
# requests one current-frame description when the worker is not busy.
# --scene-interval controls source-video seconds between background requests.
/home/rguktrkvalley/Pictures/Vision/venv/bin/python \
  -m smart_assist.detection.preview_player \
  video.mp4 \
  --sample-fps 2 \
  --max-frames 20 \
  --display \
  --mistral-scene \
  --scene-interval 5