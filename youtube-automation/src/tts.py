import edge_tts
import asyncio
import json
from pathlib import Path

VOICES = {
    "narrator_male": "en-US-ChristopherNeural",
    "narrator_female": "en-US-JennyNeural",
    "male_us": "en-US-GuyNeural",
    "female_us": "en-US-AriaNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_uk": "en-GB-SoniaNeural",
}


async def _generate(text: str, voice: str, audio_path: Path):
    words = []
    communicate = edge_tts.Communicate(text, voice)
    with open(audio_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "word": chunk["text"],
                    "start": chunk["offset"] / 10_000_000,
                    "duration": chunk["duration"] / 10_000_000,
                })
    return words


def generate_speech(text: str, voice_key: str, output_dir: Path):
    voice = VOICES.get(voice_key, VOICES["narrator_male"])
    audio_path = output_dir / "voiceover.mp3"
    words = asyncio.run(_generate(text, voice, audio_path))
    return audio_path, words
