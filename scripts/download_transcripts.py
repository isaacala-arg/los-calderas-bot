"""
Pipeline de descarga de transcripciones de YouTube para entrenamiento del bot.

USO:
  python scripts/download_transcripts.py

REQUISITOS:
  pip install yt-dlp
  (ffmpeg opcional pero recomendado — instalar desde https://ffmpeg.org/)

El script usa las cookies de tu navegador (--cookies-from-browser chrome) para
evitar los bloqueos 429 de YouTube. Asegúrate de tener Chrome abierto y haber
accedido a YouTube recientemente.
"""

import os
import re
import sys
import time
import json
import random
import subprocess
from pathlib import Path
from datetime import datetime

# ─── CONFIG ───────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent / "transcripciones"

# Canales objetivo: (slug_carpeta, url_canal, videos_a_descargar)
CHANNELS = [
    ("autodinamico",    "https://www.youtube.com/@autodinamico/videos",    12),
    ("gabo-salazar",    "https://www.youtube.com/@GaboSalazar/videos",     12),
    ("manuela-vazquez", "https://www.youtube.com/@manuelavazquezdriving/videos", 12),
    ("virales-automotriz", None, 0),  # se llena con VIRAL_URLS abajo
]

# Videos virales hardcodeados (top automotriz México)
VIRAL_URLS = [
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # placeholder — reemplaza con URLs reales
]

MIN_DURATION_SEC = 180   # solo videos de +3 min (más contenido real)
MAX_VIDEOS_PER_CHANNEL = 12
SLEEP_BETWEEN_VIDEOS = (8, 18)   # segundos aleatorios entre descargas

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[áàä]", "a", text)
    text = re.sub(r"[éèë]", "e", text)
    text = re.sub(r"[íìï]", "i", text)
    text = re.sub(r"[óòö]", "o", text)
    text = re.sub(r"[úùü]", "u", text)
    text = re.sub(r"[ñ]", "n", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    return text.strip("-")[:80]


def run(cmd: list[str]) -> tuple[int, str, str]:
    """Run a command, return (returncode, stdout, stderr)."""
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result.returncode, result.stdout, result.stderr


def yt_dlp_base() -> list[str]:
    """Base yt-dlp command with cookie + anti-bot options."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--no-check-certificate",
        "--no-playlist",
        "--quiet",
        "--no-warnings",
    ]
    # Try to use Chrome cookies to bypass 429/bot detection
    try:
        code, _, _ = run([sys.executable, "-m", "yt_dlp", "--cookies-from-browser", "chrome",
                          "--skip-download", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"])
        cmd += ["--cookies-from-browser", "chrome"]
        print("  ✅ Usando cookies de Chrome")
    except Exception:
        print("  ⚠️  Sin cookies de Chrome — puede haber bloqueos 429")
    return cmd


# ─── VTT → MARKDOWN ───────────────────────────────────────────────────────────

def vtt_to_clean_text(vtt_path: Path) -> str:
    """Convert a .vtt subtitle file to clean readable text."""
    raw = vtt_path.read_text(encoding="utf-8", errors="replace")

    lines = raw.splitlines()
    text_lines = []
    for line in lines:
        # Skip header, metadata, timestamps, and numeric cue IDs
        if re.match(r"^WEBVTT", line): continue
        if re.match(r"^(Kind|Language|NOTE|STYLE|REGION):", line): continue
        if re.match(r"^\d{2}:\d{2}", line): continue        # timestamp
        if re.match(r"^\d+$", line.strip()): continue       # numeric cue ID
        if re.match(r"^align:", line): continue              # cue settings
        # Strip inline timing tags: <00:00:00.000> <c> </c>
        cleaned = re.sub(r"<[^>]+>", "", line).strip()
        if cleaned:
            text_lines.append(cleaned)

    # YouTube auto-subs use a rolling window — consecutive lines heavily overlap.
    # Strategy: keep a line only if it doesn't start with the ending of the previous line.
    deduped = []
    for line in text_lines:
        if not deduped:
            deduped.append(line)
            continue
        prev = deduped[-1]
        # Skip if exact duplicate
        if line == prev:
            continue
        # Skip if line is contained in prev (YouTube repeated subset)
        if line in prev:
            continue
        # Skip if prev ends with the start of this line (rolling overlap)
        # Check the last 30 chars of prev vs first 30 of current
        tail = prev[-30:].lower().strip()
        head = line[:30].lower().strip()
        if tail and head and (head.startswith(tail) or tail.endswith(head)):
            # Append only the new part
            overlap_end = prev.lower().rfind(line[:20].lower())
            if overlap_end > 0:
                new_part = line[len(prev) - overlap_end:].strip()
                if new_part:
                    deduped[-1] = prev + " " + new_part
                continue
        deduped.append(line)

    # Join into readable paragraphs (~6 lines each)
    paragraphs = []
    chunk = []
    for line in deduped:
        chunk.append(line)
        if len(chunk) >= 6:
            paragraphs.append(" ".join(chunk))
            chunk = []
    if chunk:
        paragraphs.append(" ".join(chunk))

    return "\n\n".join(paragraphs)


def write_markdown(out_path: Path, meta: dict, transcript: str):
    content = f"""# {meta['title']}
**Canal:** {meta['channel']}
**URL:** {meta['url']}
**Fecha:** {meta.get('upload_date', 'desconocida')}
**Duración:** {meta.get('duration_str', 'desconocida')}

---

{transcript}
"""
    out_path.write_text(content, encoding="utf-8")


# ─── DOWNLOAD LOGIC ───────────────────────────────────────────────────────────

def get_channel_video_urls(channel_url: str, max_videos: int, base_cmd: list[str]) -> list[dict]:
    """Fetch the most recent N video URLs from a channel."""
    print(f"  Obteniendo lista de videos de {channel_url} ...")
    cmd = base_cmd + [
        "--flat-playlist",
        "--playlist-end", str(max_videos * 3),  # fetch extra to filter by duration
        "--print", "%(id)s\t%(title)s\t%(duration)s",
        channel_url,
    ]
    code, stdout, stderr = run(cmd)
    if code != 0:
        print(f"  ❌ Error obteniendo playlist: {stderr[:200]}")
        return []

    videos = []
    for line in stdout.strip().splitlines():
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        vid_id, title, duration_str = parts[0], parts[1], parts[2]
        try:
            duration = int(duration_str)
        except (ValueError, TypeError):
            duration = 0
        if duration and duration < MIN_DURATION_SEC:
            continue  # skip shorts and very short videos
        videos.append({
            "id": vid_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={vid_id}",
            "duration": duration,
            "duration_str": f"{duration // 60}:{duration % 60:02d}",
        })
        if len(videos) >= max_videos:
            break

    print(f"  → {len(videos)} videos seleccionados (+{MIN_DURATION_SEC // 60} min)")
    return videos


def download_subtitle(video: dict, out_dir: Path, base_cmd: list[str]) -> Path | None:
    """Download subtitles for one video. Returns path to .vtt file or None."""
    slug = slugify(video["title"])
    out_template = str(out_dir / f"{slug}.%(ext)s")

    for lang in ["es", "en"]:
        cmd = base_cmd + [
            "--write-auto-subs",
            "--sub-lang", lang,
            "--skip-download",
            "--sub-format", "vtt",
            "-o", out_template,
            video["url"],
        ]
        code, stdout, stderr = run(cmd)
        # Find downloaded file
        vtt_candidates = list(out_dir.glob(f"{slug}.{lang}.vtt"))
        if not vtt_candidates:
            vtt_candidates = list(out_dir.glob(f"{slug}.*.vtt"))
        if vtt_candidates:
            return vtt_candidates[0], lang
        if "429" in stderr:
            print(f"  ⚠️  Rate limit (429) — esperando 60s antes de reintentar...")
            time.sleep(60)
            code, stdout, stderr = run(cmd)
            vtt_candidates = list(out_dir.glob(f"{slug}.*.vtt"))
            if vtt_candidates:
                return vtt_candidates[0], lang

    return None, None


def process_channel(folder: str, channel_url: str | None, max_videos: int,
                    base_cmd: list[str], index_rows: list[dict]):
    out_dir = BASE_DIR / folder
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Canal: {folder}")
    print(f"{'='*60}")

    if channel_url is None:
        return  # virales handled separately

    videos = get_channel_video_urls(channel_url, max_videos, base_cmd)
    consecutive_failures = 0

    for i, video in enumerate(videos, 1):
        print(f"  [{i}/{len(videos)}] {video['title'][:60]}")
        vtt_path, lang = download_subtitle(video, out_dir, base_cmd)

        if vtt_path is None:
            print(f"    ❌ Sin subtítulos disponibles")
            consecutive_failures += 1
            if consecutive_failures >= 3:
                print(f"  ⚠️  3 fallos consecutivos — pausando {folder}. Revisa el error.")
                break
            continue

        consecutive_failures = 0
        try:
            transcript = vtt_to_clean_text(vtt_path)
            video["channel"] = folder
            md_path = out_dir / (vtt_path.stem.replace(f".{lang}", "") + ".md")
            write_markdown(md_path, video, transcript)
            vtt_path.unlink()  # remove raw .vtt
            print(f"    ✅ Guardado: {md_path.name} ({lang})")
            index_rows.append({
                "creador": folder,
                "titulo": video["title"],
                "url": video["url"],
                "duracion": video.get("duration_str", "?"),
                "idioma": lang,
                "fecha": video.get("upload_date", "?"),
                "archivo": str(md_path.relative_to(BASE_DIR)),
            })
        except Exception as e:
            print(f"    ❌ Error procesando {vtt_path}: {e}")

        # Random sleep to avoid rate limiting
        sleep_time = random.randint(*SLEEP_BETWEEN_VIDEOS)
        print(f"    ⏳ Esperando {sleep_time}s...")
        time.sleep(sleep_time)


def process_viral_urls(base_cmd: list[str], index_rows: list[dict]):
    out_dir = BASE_DIR / "virales-automotriz"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"Canal: virales-automotriz ({len(VIRAL_URLS)} URLs)")
    print(f"{'='*60}")

    if not VIRAL_URLS or VIRAL_URLS[0].endswith("dQw4w9WgXcQ"):
        print("  ⚠️  VIRAL_URLS tiene solo placeholders — edita el script con URLs reales")
        return

    for i, url in enumerate(VIRAL_URLS, 1):
        # Get video info first
        info_cmd = base_cmd + ["--print", "%(title)s\t%(duration)s\t%(channel)s", url]
        code, stdout, _ = run(info_cmd)
        parts = stdout.strip().split("\t")
        title = parts[0] if parts else url
        duration = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
        channel = parts[2] if len(parts) > 2 else "viral"

        video = {
            "title": title,
            "url": url,
            "channel": channel,
            "duration": duration,
            "duration_str": f"{duration // 60}:{duration % 60:02d}",
        }

        print(f"  [{i}/{len(VIRAL_URLS)}] {title[:60]}")
        vtt_path, lang = download_subtitle(video, out_dir, base_cmd)
        if vtt_path:
            transcript = vtt_to_clean_text(vtt_path)
            slug = slugify(title)
            md_path = out_dir / f"{slug}.md"
            write_markdown(md_path, video, transcript)
            vtt_path.unlink()
            print(f"    ✅ {md_path.name} ({lang})")
            index_rows.append({
                "creador": "virales-automotriz",
                "titulo": title,
                "url": url,
                "duracion": video.get("duration_str", "?"),
                "idioma": lang,
                "fecha": "?",
                "archivo": str(md_path.relative_to(BASE_DIR)),
            })
        time.sleep(random.randint(*SLEEP_BETWEEN_VIDEOS))


def write_index(index_rows: list[dict]):
    lines = [
        "# Índice de Transcripciones — Los Calderas Bot",
        f"\n_Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n",
        f"**Total:** {len(index_rows)} transcripciones\n",
        "| Creador | Título | Duración | Idioma | URL |",
        "|---------|--------|----------|--------|-----|",
    ]
    for row in index_rows:
        title_short = row["titulo"][:50] + ("..." if len(row["titulo"]) > 50 else "")
        lines.append(
            f"| {row['creador']} | [{title_short}]({row['archivo']}) "
            f"| {row['duracion']} | {row['idioma']} | {row['url']} |"
        )
    (BASE_DIR / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n📋 INDEX.md actualizado: {len(index_rows)} entradas")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    print("🚗 Los Calderas — Pipeline de transcripciones de YouTube")
    print(f"📁 Destino: {BASE_DIR}\n")

    base_cmd = yt_dlp_base()
    index_rows = []

    for folder, channel_url, max_videos in CHANNELS:
        if folder == "virales-automotriz":
            process_viral_urls(base_cmd, index_rows)
        else:
            process_channel(folder, channel_url, max_videos, base_cmd, index_rows)

    write_index(index_rows)
    print(f"\n✅ Pipeline completo. {len(index_rows)} transcripciones guardadas en {BASE_DIR}")


if __name__ == "__main__":
    main()
