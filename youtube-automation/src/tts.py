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

# Chunk size: split long scripts to ensure WordBoundary events are received
_CHUNK_WORDS = 200


def _split_text(text: str) -> list:
    words = text.split()
    chunks = []
    for i in range(0, len(words), _CHUNK_WORDS):
        chunks.append(" ".join(words[i:i + _CHUNK_WORDS]))
    return chunks or [text]


async def _generate_chunk(text: str, voice: str, audio_path: Path) -> list:
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


async def _generate_all(text: str, voice: str, audio_path: Path) -> list:
    chunks = _split_text(text)
    if len(chunks) == 1:
        return await _generate_chunk(text, voice, audio_path)

    # Multiple chunks: generate each separately then merge audio files
    import subprocess
    tmp = audio_path.parent / "chunks"
    tmp.mkdir(exist_ok=True)

    all_words = []
    time_offset = 0.0
    chunk_files = []

    for i, chunk_text in enumerate(chunks):
        chunk_path = tmp / f"chunk_{i}.mp3"
        words = await _generate_chunk(chunk_text, voice, chunk_path)
        # Shift word timestamps by current offset
        for w in words:
            all_words.append({
                "word": w["word"],
                "start": w["start"] + time_offset,
                "duration": w["duration"],
            })
        chunk_files.append(str(chunk_path))
        # Get duration of this chunk audio
        if words:
            last = words[-1]
            time_offset += last["start"] + last["duration"] + 0.05

    # Concatenate audio files with ffmpeg
    list_file = tmp / "chunks.txt"
    with open(list_file, "w") as f:
        for p in chunk_files:
            f.write(f"file '{p}'\n")
    subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", "-y", str(audio_path)],
        capture_output=True,
    )
    return all_words


def generate_speech(text: str, voice_key: str, output_dir: Path):
    voice = VOICES.get(voice_key, VOICES["narrator_male"])
    audio_path = output_dir / "voiceover.mp3"
    words = asyncio.run(_generate_all(text, voice, audio_path))
    return audio_path, words
