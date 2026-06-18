#!/usr/bin/env python3
"""
Додає voice_track.mp3 до bvd_v2.mp4
Запусти після generate_voice.py:
  python3 add_voice.py

Виводить: bvd_v2_voiced.mp4
"""
import os, subprocess
import imageio_ffmpeg

_HERE  = os.path.dirname(os.path.abspath(__file__))
VIDEO  = os.path.join(_HERE, "bvd_v2.mp4")
VOICE  = os.path.join(_HERE, "voice_track.mp3")
OUTPUT = os.path.join(_HERE, "bvd_v2_voiced.mp4")

if not os.path.exists(VIDEO):
    print(f"ERROR: {VIDEO} not found — render the video first")
    exit(1)
if not os.path.exists(VOICE):
    print(f"ERROR: {VOICE} not found — run generate_voice.py first")
    exit(1)

ff = imageio_ffmpeg.get_ffmpeg_exe()

# Mix: voice at 0.9 volume on top of existing audio track
# If video has no audio — just attach voice
cmd = [
    ff, "-y",
    "-i", VIDEO,
    "-i", VOICE,
    "-filter_complex",
    "[0:a][1:a]amix=inputs=2:duration=first:weights=1 0.85[aout]",
    "-map", "0:v",
    "-map", "[aout]",
    "-c:v", "copy",
    "-c:a", "aac", "-b:a", "160k",
    OUTPUT
]

print(f"Mixing voice into video...")
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    # Fallback: video might have no audio stream
    cmd2 = [
        ff, "-y",
        "-i", VIDEO,
        "-i", VOICE,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "160k",
        "-shortest",
        OUTPUT
    ]
    subprocess.run(cmd2, check=True)

print(f"✓ Done: {OUTPUT}")
print(f"  Play: open {OUTPUT}")
