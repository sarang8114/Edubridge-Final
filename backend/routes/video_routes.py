import traceback
from flask import Blueprint, request, jsonify, send_file
from services.video_service import generate_concept_video
from utils.gemini_client import initialize_imageprompt_client
import os

video_bp = Blueprint("video", __name__)


@video_bp.route("/generate-video", methods=["POST"])
def generate_video():
    try:
        body     = request.get_json()
        text     = body.get("text", "").strip()
        images   = body.get("images", [])
        language = body.get("language", "english")

        if not text:
            return jsonify({"success": False, "message": "text is required"}), 400
        if not images:
            return jsonify({"success": False, "message": "images are required"}), 400

        print(f"[ROUTE] /generate-video: {len(images)} images, language={language}")

        client = initialize_imageprompt_client()
        result = generate_concept_video(client, text, images, language)

        filename  = os.path.basename(result["video_path"])
        video_url = f"/video/{filename}"

        return jsonify({
            "success": True,
            "data": {
                "video_url": video_url,
                "title": result["title"],
                "segments": result["segments"]
            }
        })

    except ValueError as e:
        print(f"[ROUTE] ValueError: {e}")
        return jsonify({"success": False, "message": str(e)}), 400
    except Exception as e:
        # Print full traceback so you can see the real error in terminal
        print(f"[ROUTE] Exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"{type(e).__name__}: {e}"}), 500


@video_bp.route("/video/<filename>", methods=["GET"])
def serve_video(filename):
    video_path = os.path.join("uploads", "videos", filename)
    if not os.path.exists(video_path):
        return jsonify({"error": "Video not found"}), 404

    return send_file(
        video_path,
        mimetype="video/mp4",
        as_attachment=False,
        conditional=True
    )