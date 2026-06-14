import re
import json
import asyncio
import subprocess
from pathlib import Path

import edge_tts

VOICES = {
    "narrator_male": "en-US-ChristopherNeural",
    "narrator_female": "en-US-JennyNeural",
    "male_us": "en-US-GuyNeural",
    "female_us": "en-US-AriaNeural",
    "male_uk": "en-GB-RyanNeural",
    "female_uk": "en-GB-SoniaNeural",
}

# Max words per TTS request — edge-tts loses WordBoundary events on very long texts
_CHUNK_WORDS = 350


def _split_chunks(text: str) -> list:
    """Split at sentence boundaries so each chunk ≤ _CHUNK_WORDS words."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, buf, count = [], [], 0
    for s in sentences:
        n = len(s.split())
        if count + n > _CHUNK_WORDS and buf:
            chunks.append(" ".join(buf))
            buf, count = [s], n
        else:
            buf.append(s)
            count += n
    if buf:
        chunks.append(" ".join(buf))
    return chunks or [text]


async def _generate_chunk(text: str, voice: str, path: Path) -> list:
    words = []
    comm = edge_tts.Communicate(text, voice, rate="-5%")
    with open(path, "wb") as f:
        async for chunk in comm.stream():
            t = chunk.get("type", "")
            if t == "audio":
                f.write(chunk["data"])
            elif t == "WordBoundary":
                words.append({
                    "word": chunk.get("text", ""),
                    "start": chunk.get("offset", 0) / 10_000_000,
                    "duration": chunk.get("duration", 0) / 10_000_000,
                })
    return words


def _duration(path: Path) -> float:
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    try:
        return float(json.loads(r.stdout)["format"]["duration"])
    except Exception:
        return 0.0


def generate_speech(text: str, voice_key: str, output_dir: Path):
    voice = VOICES.get(voice_key, VOICES["narrator_male"])
    audio_path = output_dir / "voiceover.mp3"

    chunks = _split_chunks(text)
    print(f"  TTS: {len(chunks)} chunk(s), voice={voice}")

    all_words = []
    chunk_paths = []
    offset = 0.0

    for i, chunk_text in enumerate(chunks):
        cpath = output_dir / f"chunk_{i}.mp3"
        chunk_paths.append(cpath)

        words = asyncio.run(_generate_chunk(chunk_text, voice, cpath))

        if not cpath.exists():
            raise RuntimeError(f"TTS failed on chunk {i}")

        dur = _duration(cpath)

        if words:
            for w in words:
                all_words.append({
                    "word": w["word"],
                    "start": w["start"] + offset,
                    "duration": w["duration"],
                })
        else:
            # Fallback for this chunk: evenly distribute
            raw = chunk_text.split()
            if dur > 0 and raw:
                gap = dur / len(raw)
                for j, w in enumerate(raw):
                    all_words.append({
                        "word": w,
                        "start": offset + j * gap,
                        "duration": gap * 0.85,
                    })

        offset += dur
        print(f"    chunk {i+1}/{len(chunks)}: {len(words)} timestamps, {dur:.1f}s")

    # Concatenate chunks
    if len(chunk_paths) == 1:
        chunk_paths[0].rename(audio_path)
    else:
        list_file = output_dir / "chunks.txt"
        list_file.write_text(
            "\n".join(f"file '{p.name}'" for p in chunk_paths)
        )
        subprocess.run(
            ["ffmpeg", "-f", "concat", "-safe", "0",
             "-i", str(list_file), "-c", "copy", "-y", str(audio_path)],
            capture_output=True,
        )
        list_file.unlink(missing_ok=True)
        for p in chunk_paths:
            p.unlink(missing_ok=True)

    if not audio_path.exists():
        raise RuntimeError("TTS failed: voiceover.mp3 not created")

    return audio_path, all_words
