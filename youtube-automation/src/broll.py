import requests
import subprocess
from pathlib import Path

STOPWORDS = {
    "that", "this", "with", "from", "they", "their", "what", "will", "never",
    "people", "have", "been", "when", "your", "more", "just", "into", "over",
    "also", "very", "some", "make", "like", "time", "only", "need", "most",
    "every", "even", "than", "those", "know", "well", "such", "many", "would",
    "according", "because", "without", "before", "after", "about", "percent",
    "should", "could", "there", "these", "those", "then", "them", "were",
}

# Words that produce good B-roll on Pexels
BROLL_SYNONYMS = {
    "rich": "wealth luxury",
    "money": "money cash",
    "invest": "investment finance",
    "investor": "stock market",
    "business": "business office",
    "market": "stock market trading",
    "stock": "stock market",
    "wealth": "wealth luxury",
    "success": "success achievement",
    "bank": "banking finance",
    "financial": "finance money",
    "profit": "profit growth",
    "income": "income money",
    "saving": "savings bank",
    "economy": "economy finance",
    "work": "work office",
    "learn": "education learning",
    "knowledge": "education books",
    "discipline": "focus discipline",
    "growth": "growth chart",
}


def _keywords(topic: str, script: str) -> list:
    all_words = (topic + " " + script).lower().split()
    cleaned = [w.strip(".,!?\"'()%0123456789:;—") for w in all_words]

    seen, result = set(), []
    for w in cleaned:
        if len(w) > 4 and w not in STOPWORDS and w not in seen:
            seen.add(w)
            # Map to a better search query if available
            result.append(BROLL_SYNONYMS.get(w, w))
        if len(result) >= 8:
            break
    return result


def _search_videos(query: str, api_key: str, count: int = 2) -> list:
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
    """Re-encode with cinematic color grade baked in via ffmpeg."""
    result = subprocess.run(
        ["ffmpeg", "-i", str(src),
         "-vf", "colorchannelmixer=rr=1.06:bb=0.88,eq=brightness=-0.12:saturation=1.1",
         "-c:v", "libx264", "-preset", "ultrafast",
         "-pix_fmt", "yuv420p", "-an",
         "-y", str(dst)],
        capture_output=True,
        timeout=120,
    )
    return result.returncode == 0


def fetch_broll(topic: str, script: str, api_key: str, output_dir: Path, count: int = 8) -> list:
    keywords = _keywords(topic, script)
    clips = []
    for i, kw in enumerate(keywords):
        for j, url in enumerate(_search_videos(kw, api_key, count=2)):
            raw = output_dir / f"broll_raw_{i}_{j}.mp4"
            ready = output_dir / f"broll_{i}_{j}.mp4"
            if _download(url, raw) and _transcode(raw, ready):
                clips.append(ready)
                raw.unlink(missing_ok=True)
                print(f"    clip {len(clips)}: '{kw}'")
            if len(clips) >= count:
                return clips
    return clips
