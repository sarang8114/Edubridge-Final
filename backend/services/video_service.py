import os
import uuid
import json
import tempfile
import subprocess
import requests
import numpy as np

from utils.gemini_client import MODEL
from services.audio_service import generate_audio_stream


# ── Step 1: Generate narration script ────────────────────────────────────────

def generate_video_script(client, simplified_text: str, images: list) -> dict:
    image_titles = [img.get("title", f"Image {i+1}") for i, img in enumerate(images)]

    messages = [
        {
            "role": "system",
            "content": (
                "You are an expert educational video scriptwriter for school students. "
                "Write clear, simple, engaging narration for concept explanation videos. "
                "Return ONLY valid JSON."
            )
        },
        {
            "role": "user",
            "content": f"""
You are creating a short educational video for students.

The video will show {len(images)} images in sequence. Each image illustrates one concept.

Image titles (in order):
{json.dumps(image_titles, indent=2)}

Simplified educational text:
--------------------
{simplified_text}
--------------------

Write a narration script for each image segment. Each segment should:
- Be 2-4 sentences long
- Be simple and engaging for school students
- Directly relate to what the image shows
- Flow naturally from one segment to the next
- Avoid technical jargon

OUTPUT FORMAT (strict JSON only):
{{
  "title": "Short video title based on the topic",
  "segments": [
    {{
      "image_index": 0,
      "image_title": "{image_titles[0] if image_titles else 'Image 1'}",
      "narration": "2-4 sentence narration for this image..."
    }}
  ]
}}

Generate exactly {len(images)} segments, one per image.
Return ONLY valid JSON with no extra text.
"""
        }
    ]

    resp = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        response_format={"type": "json_object"}
    )
    return json.loads(resp.choices[0].message.content)


# ── Step 2: Download image ────────────────────────────────────────────────────

def download_image(url: str, dest_path: str) -> bool:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(r.content)
        return True
    except Exception as e:
        print(f"[VIDEO] Image download error: {e}")
        return False


# ── Step 3: Get audio duration via ffprobe ────────────────────────────────────

def get_audio_duration(audio_path: str) -> float:
    """Get audio duration in seconds."""
    # Method 1: mutagen (most reliable, pure Python)
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        duration = audio.info.length
        print(f"[VIDEO] Duration via mutagen: {duration:.2f}s")
        return duration
    except Exception as e:
        print(f"[VIDEO] mutagen failed: {e}")

    # Method 2: imageio_ffmpeg bundled ffmpeg
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        result = subprocess.run(
            [ffmpeg, "-i", audio_path],
            capture_output=True, text=True, timeout=10
        )
        # ffmpeg prints duration to stderr: "Duration: 00:00:08.45"
        import re
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.?\d*)", result.stderr)
        if match:
            h, m, s = match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)
            print(f"[VIDEO] Duration via ffmpeg stderr: {duration:.2f}s")
            return duration
    except Exception as e:
        print(f"[VIDEO] ffmpeg duration failed: {e}")

    print("[VIDEO] Duration fallback: 4.0s")
    return 4.0

# ── Step 4: Build one segment video (image + audio) via ffmpeg ───────────────

def build_segment(img_path: str, audio_path: str, out_path: str, duration: float) -> bool:
    """Use ffmpeg directly to create a video segment from one image + one audio."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        cmd = [
            ffmpeg, "-y",
            "-loop", "1",               # loop the image
            "-i", img_path,             # input: image
            "-i", audio_path,           # input: audio
            "-c:v", "libx264",
            "-tune", "stillimage",      # optimise for still images
            "-c:a", "aac",
            "-b:a", "128k",
            "-pix_fmt", "yuv420p",      # max browser compatibility
            "-t", str(duration),        # stop at audio length
            "-vf", "scale=512:512:force_original_aspect_ratio=decrease,pad=512:512:(ow-iw)/2:(oh-ih)/2",
            "-shortest",
            out_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            print(f"[VIDEO] ffmpeg segment error: {result.stderr[-500:]}")
            return False
        return True

    except Exception as e:
        print(f"[VIDEO] build_segment error: {e}")
        return False


# ── Step 5: Concatenate segment videos via ffmpeg ────────────────────────────

def concatenate_segments(segment_paths: list, output_path: str) -> bool:
    """Concatenate multiple MP4 segments into one final MP4 using ffmpeg concat."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

        # Write concat list file
        tmp_dir   = os.path.dirname(output_path)
        list_path = os.path.join(tmp_dir, "concat_list.txt")

        with open(list_path, "w") as f:
            for p in segment_paths:
                f.write(f"file '{os.path.abspath(p)}'\n")

        cmd = [
            ffmpeg, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", list_path,
            "-c", "copy",        # no re-encode — fast
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        try:
            os.remove(list_path)
        except Exception:
            pass

        if result.returncode != 0:
            print(f"[VIDEO] ffmpeg concat error: {result.stderr[-500:]}")
            return False
        return True

    except Exception as e:
        print(f"[VIDEO] concatenate_segments error: {e}")
        return False


# ── Main orchestrator ─────────────────────────────────────────────────────────

def generate_concept_video(client, simplified_text: str, images: list, language: str = "english") -> dict:
    valid_images = [img for img in images if img.get("image_url") and not img.get("error")]
    if not valid_images:
        raise ValueError(f"No valid images for video. Got {len(images)} images, {len(valid_images)} usable.")

    print(f"[VIDEO] Starting with {len(valid_images)} valid images")

    # 1. Script
    print("[VIDEO] Generating script...")
    script   = generate_video_script(client, simplified_text, valid_images)
    segments = script.get("segments", [])
    title    = script.get("title", "Concept Video")
    print(f"[VIDEO] Script: '{title}', {len(segments)} segments")

    if not segments:
        raise ValueError("Script generation returned no segments.")

    # 2. Download images + TTS
    tmp_dir = tempfile.mkdtemp(prefix="edubridge_video_")
    segment_video_paths = []
    temp_files = []

    for i, (img, seg) in enumerate(zip(valid_images, segments)):
        print(f"[VIDEO] Segment {i+1}/{len(valid_images)}...")

        # Image
        img_url  = img.get("image_url", "")
        img_ext  = "webp" if img_url.lower().endswith(".webp") else "jpg"
        img_path = os.path.join(tmp_dir, f"img_{i}.{img_ext}")

        if not download_image(img_url, img_path):
            print(f"[VIDEO] Segment {i}: image download failed, skipping")
            continue

        temp_files.append(img_path)

        # Audio (TTS)
        narration   = seg.get("narration", "").strip() or "."
        audio_bytes = generate_audio_stream(narration, language)
        audio_path  = os.path.join(tmp_dir, f"audio_{i}.mp3")

        if audio_bytes and len(audio_bytes) > 100:
            with open(audio_path, "wb") as f:
                f.write(audio_bytes)
            print(f"[VIDEO] Segment {i}: audio OK ({len(audio_bytes)} bytes)")
        else:
            print(f"[VIDEO] Segment {i}: TTS failed, using silence")
            _write_silent_mp3(audio_path, duration=4.0)

        temp_files.append(audio_path)

        # Get duration and build segment video
        duration  = get_audio_duration(audio_path)
        seg_path  = os.path.join(tmp_dir, f"seg_{i}.mp4")

        if build_segment(img_path, audio_path, seg_path, duration):
            segment_video_paths.append(seg_path)
            temp_files.append(seg_path)
            print(f"[VIDEO] Segment {i}: video built ({duration:.1f}s)")
        else:
            print(f"[VIDEO] Segment {i}: video build failed, skipping")

    if not segment_video_paths:
        raise RuntimeError("All segments failed — could not build any video segments.")

    # 3. Concatenate
    video_id    = str(uuid.uuid4())[:8]
    output_dir  = os.path.join("uploads", "videos")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"concept_{video_id}.mp4")

    if len(segment_video_paths) == 1:
        # Only one segment — just move it
        import shutil
        shutil.move(segment_video_paths[0], output_path)
        print(f"[VIDEO] Single segment, moved to: {output_path}")
    else:
        print(f"[VIDEO] Concatenating {len(segment_video_paths)} segments...")
        if not concatenate_segments(segment_video_paths, output_path):
            raise RuntimeError("Failed to concatenate video segments.")

    print(f"[VIDEO] Done: {output_path}")

    # Cleanup
    for p in temp_files:
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        os.rmdir(tmp_dir)
    except Exception:
        pass

    return {
        "video_path": output_path,
        "title": title,
        "segments": segments
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_silent_mp3(path: str, duration: float = 4.0):
    """Generate a silent MP3 using ffmpeg."""
    try:
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg, "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=stereo",
            "-t", str(duration),
            "-q:a", "9",
            "-acodec", "libmp3lame",
            path
        ]
        subprocess.run(cmd, capture_output=True, timeout=15)
    except Exception as e:
        print(f"[VIDEO] Silent MP3 error: {e}")
        open(path, "wb").close()