import requests
import subprocess
from pathlib import Path


def _keywords(topic: str, script: str) -> list:
    kw = [w.lower() for w in topic.split() if len(w) > 3]
    words = script.split()
    for i in range(0, len(words), 60):
        w = words[i].lower().strip(".,!?\"'")
        if len(w) > 4:
            kw.append(w)
    seen = set()
    result = []
    for k in kw:
        if k not in seen:
            seen.add(k)
            result.append(k)
    return result[:5]


def _search_videos(query: str, api_key: str, count: int = 3) -> list:
    resp = requests.get(
        "https://api.pexels.com/videos/search",
        headers={"Authorization": api_key},
        params={"query": query, "per_page": count, "orientation": "landscape"},
        timeout=15,
    )
    if resp.status_code != 200:
        return []
    urls = []
    for video in resp.json().get("videos", []):
        files = video.get("video_files", [])
        hd = [f for f in files if f.get("quality") == "hd" and f.get("width", 0) >= 1280]
        chosen = hd[0] if hd else (files[0] if files else None)
        if chosen:
            urls.append(chosen["link"])
    return urls


def _download(url: str, path: Path) -> bool:
    try:
        resp = requests.get(url, stream=True, timeout=60)
        if resp.status_code != 200:
            return False
        with open(path, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception:
        return False


def _transcode(src: Path, dst: Path) -> bool:
    """Re-encode to H.264 yuv420p so moviepy can always open it."""
    result = subprocess.run(
        [
            "ffmpeg", "-i", str(src),
            "-c:v", "libx264", "-preset", "ultrafast",
            "-pix_fmt", "yuv420p", "-an",
            "-y", str(dst),
        ],
        capture_output=True,
        timeout=120,
    )
    return result.returncode == 0


def fetch_broll(topic: str, script: str, api_key: str, output_dir: Path, count: int = 6) -> list:
    keywords = _keywords(topic, script)
    clips = []
    for i, kw in enumerate(keywords[:3]):
        for j, url in enumerate(_search_videos(kw, api_key, count=2)):
            raw = output_dir / f"broll_raw_{i}_{j}.mp4"
            ready = output_dir / f"broll_{i}_{j}.mp4"
            if _download(url, raw) and _transcode(raw, ready):
                clips.append(ready)
                raw.unlink(missing_ok=True)
                print(f"    clip {len(clips)}: {kw}")
            if len(clips) >= count:
                return clips
    return clips
