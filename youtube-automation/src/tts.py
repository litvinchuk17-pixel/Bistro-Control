import edge_tts
import asyncio
from pathlib import Path

VOICES = {
    "narrator_male": "en-US-ChristopherNeural",
    "narrator_female": "en-US-JennyNeural",
    "male_us": "en-US-GuyNeural",
    "female_us": "en-US-AriaNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_uk": "en-GB-SoniaNeural",
}


async def _generate(text: str, voice: str, audio_path: Path) -> list:
    words = []
    communicate = edge_tts.Communicate(text, voice)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            ctype = chunk.get("type", "")
            if ctype == "audio":
                f.write(chunk["data"])
            elif ctype == "WordBoundary":
                words.append({
                    "word": chunk.get("text", ""),
                    "start": chunk.get("offset", 0) / 10_000_000,
                    "duration": chunk.get("duration", 0) / 10_000_000,
                })
    return words


def _estimate_timing(text: str, audio_duration: float) -> list:
    """Fallback: distribute words evenly across audio duration."""
    raw_words = text.split()
    if not raw_words:
        return []
    gap = audio_duration / len(raw_words)
    result = []
    for i, w in enumerate(raw_words):
        result.append({
            "word": w,
            "start": i * gap,
            "duration": gap * 0.85,
        })
    return result


def generate_speech(text: str, voice_key: str, output_dir: Path):
    voice = VOICES.get(voice_key, VOICES["narrator_male"])
    audio_path = output_dir / "voiceover.mp3"

    words = asyncio.run(_generate(text, voice, audio_path))

    if not audio_path.exists():
        raise RuntimeError("TTS failed: voiceover.mp3 was not created")

    if not words:
        # edge-tts didn't return WordBoundary events — estimate from duration
        import subprocess, json
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(audio_path)],
            capture_output=True, text=True,
        )
        duration = 0.0
        try:
            info = json.loads(probe.stdout)
            duration = float(info["format"]["duration"])
        except Exception:
            pass
        if duration > 0:
            words = _estimate_timing(text, duration)
            print(f"  (using estimated subtitle timing, {len(words)} words)")

    return audio_path, words
