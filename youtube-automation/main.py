#!/usr/bin/env python3
"""YouTube Automation - CLI tool to generate faceless YouTube videos."""

import json
import os
import shutil
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.tts import generate_speech, VOICES
from src.broll import fetch_broll
from src.video import assemble_video
from src.thumbnail import create_thumbnail


BANNER = """
╔══════════════════════════════════════════════════╗
║        YouTube Automation Tool  v1.0             ║
║  edge-tts + Pexels + MoviePy  |  100% Free       ║
╚══════════════════════════════════════════════════╝
"""


def ask(prompt: str, default: str = None) -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{prompt}{suffix}: ").strip()
    return val if val else (default or "")


def pick_voice() -> str:
    keys = list(VOICES.keys())
    print("\nAvailable voices:")
    for i, k in enumerate(keys, 1):
        print(f"  {i}. {k:20s}  ({VOICES[k]})")
    while True:
        raw = input(f"\nChoose voice [1]: ").strip() or "1"
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(keys):
                return keys[idx]
        except ValueError:
            pass
        print("  Invalid — try again.")


def read_script() -> str:
    print("\nPaste your script. Type ### on a new line when done:")
    lines = []
    while True:
        line = input()
        if line.strip() == "###":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    print(BANNER)

    pexels_key = os.getenv("PEXELS_API_KEY", "").strip()
    if not pexels_key:
        print("No PEXELS_API_KEY in .env  (get one free at https://www.pexels.com/api/)")
        pexels_key = input("Enter Pexels API key (or Enter to skip B-roll): ").strip()

    print("\n--- STEP 1: Topic ---")
    topic = ask("Video topic (e.g. 'The Fall of the Roman Empire')")
    if not topic:
        sys.exit("Topic cannot be empty.")

    print("\n--- STEP 2: Script ---")
    script = read_script()
    if not script:
        sys.exit("Script cannot be empty.")

    print("\n--- STEP 3: Voice ---")
    voice_key = pick_voice()

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic)[:40].lower()
    out_dir = Path("output") / safe_name
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp_dir = out_dir / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    print(f"\n{'='*52}")
    print(f"  Building: {topic}")
    print(f"{'='*52}\n")

    print("Generating voiceover...")
    audio_path, words = generate_speech(script, voice_key, tmp_dir)
    print(f"  voiceover.mp3  ({len(words)} word timestamps)\n")

    broll_clips = []
    if pexels_key:
        print("Fetching B-roll from Pexels...")
        broll_clips = fetch_broll(topic, script, pexels_key, tmp_dir, count=6)
        print(f"  {len(broll_clips)} clips downloaded\n")
    else:
        print("  Skipping B-roll (no API key)\n")

    print("Assembling video...")
    video_path = out_dir / f"{safe_name}.mp4"
    bgm = Path("assets/bgm.mp3")
    assemble_video(broll_clips, audio_path, words, video_path, bgm if bgm.exists() else None)
    print(f"  {video_path}\n")

    print("Creating thumbnail...")
    thumb_path = out_dir / f"{safe_name}_thumbnail.jpg"
    create_thumbnail(topic, output_path=thumb_path)
    print(f"  {thumb_path}\n")

    shutil.rmtree(tmp_dir, ignore_errors=True)

    info = {
        "topic": topic,
        "voice": voice_key,
        "words_in_script": len(script.split()),
        "video": str(video_path),
        "thumbnail": str(thumb_path),
    }
    with open(out_dir / "project.json", "w") as f:
        json.dump(info, f, indent=2)

    print(f"{'='*52}")
    print(f"  DONE!")
    print(f"  Video:     {video_path}")
    print(f"  Thumbnail: {thumb_path}")
    print(f"{'='*52}\n")


if __name__ == "__main__":
    main()
