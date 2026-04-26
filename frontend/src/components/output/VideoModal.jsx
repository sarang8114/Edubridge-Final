import { X, Loader, Play, Video } from "lucide-react";
import { useRef, useState } from "react";

const VideoModal = ({ selectedTopic, onClose, onGenerate, isGenerating, videoData, error, onRetry }) => {
  const videoRef = useRef(null);
  const [activeSegment, setActiveSegment] = useState(0);

  // Sync active segment highlight with video playback time
  const handleTimeUpdate = () => {
    if (!videoRef.current || !videoData?.segments?.length) return;
    const current  = videoRef.current.currentTime;
    const duration = videoRef.current.duration;
    if (!duration) return;
    const perSegment = duration / videoData.segments.length;
    const idx = Math.min(
      Math.floor(current / perSegment),
      videoData.segments.length - 1
    );
    setActiveSegment(idx);
  };

  const jumpToSegment = (idx) => {
    if (!videoRef.current || !videoData?.segments?.length) return;
    const duration = videoRef.current.duration;
    if (!duration) return;
    const perSegment = duration / videoData.segments.length;
    videoRef.current.currentTime = idx * perSegment;
    videoRef.current.play();
    setActiveSegment(idx);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 p-4">
      <div className="bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[92vh] flex flex-col">

        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h3 className="text-xl font-bold text-white flex items-center gap-2">
            <Video size={22} className="text-purple-400" />
            Concept Video: {selectedTopic?.topic}
          </h3>
          <button onClick={onClose} className="p-2 hover:bg-gray-700 rounded-lg transition">
            <X size={24} className="text-gray-400" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-auto p-6 space-y-6">

          {/* ── Not yet generated ── */}
          {!isGenerating && !videoData && !error && (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="w-20 h-20 bg-purple-900/30 rounded-full flex items-center justify-center">
                <Video size={40} className="text-purple-400" />
              </div>
              <p className="text-gray-300 text-lg text-center max-w-sm">
                Generate a short educational video with AI narration for <span className="text-white font-semibold">{selectedTopic?.topic}</span>
              </p>
              <p className="text-gray-500 text-sm text-center max-w-xs">
                Uses your 3 generated images + AI voiceover. Takes ~30–60 seconds.
              </p>
              <button
                onClick={onGenerate}
                className="flex items-center gap-2 px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white rounded-xl font-semibold transition"
              >
                <Play size={18} />
                Generate Video
              </button>
            </div>
          )}

          {/* ── Loading ── */}
          {isGenerating && (
            <div className="flex flex-col items-center justify-center h-64 space-y-5">
              <Loader size={48} className="animate-spin text-purple-400" />
              <div className="text-center space-y-1">
                <p className="text-gray-200 text-lg font-medium">Creating your concept video...</p>
                <p className="text-gray-500 text-sm">Writing script → generating voiceover → stitching video</p>
              </div>
              <div className="w-64 bg-gray-700 rounded-full h-1.5 overflow-hidden">
                <div className="bg-purple-500 h-full rounded-full animate-pulse w-3/4" />
              </div>
            </div>
          )}

          {/* ── Error ── */}
          {error && !isGenerating && (
            <div className="flex flex-col items-center justify-center h-64 space-y-4">
              <div className="bg-red-900/20 border border-red-500 rounded-lg p-6 max-w-md w-full">
                <p className="text-red-300 text-center mb-4">{error}</p>
                <button
                  onClick={onRetry}
                  className="w-full px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition"
                >
                  Retry
                </button>
              </div>
            </div>
          )}

          {/* ── Video ready ── */}
          {videoData && !isGenerating && (
            <div className="space-y-5">
              {/* Title */}
              <h4 className="text-white font-bold text-lg text-center">{videoData.title}</h4>

              {/* Video player */}
              <div className="rounded-xl overflow-hidden bg-black shadow-2xl">
                <video
                  ref={videoRef}
                  src={`http://127.0.0.1:5000${videoData.video_url}`} // <-- Updated to match API_BASE_URL in api.js
                  controls
                  className="w-full max-h-[50vh] object-contain"
                  onTimeUpdate={handleTimeUpdate}
                />
              </div>

              {/* Segment navigator */}
              {videoData.segments?.length > 0 && (
                <div>
                  <p className="text-gray-400 text-sm mb-3 font-medium">Jump to segment:</p>
                  <div className="space-y-2">
                    {videoData.segments.map((seg, idx) => (
                      <button
                        key={idx}
                        onClick={() => jumpToSegment(idx)}
                        className={`w-full text-left p-3 rounded-lg border transition ${
                          activeSegment === idx
                            ? "bg-purple-900/40 border-purple-500 text-white"
                            : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
                        }`}
                      >
                        <span className={`text-xs font-semibold mr-2 ${activeSegment === idx ? "text-purple-400" : "text-gray-500"}`}>
                          {idx + 1}. {seg.image_title || `Segment ${idx + 1}`}
                        </span>
                        <p className="text-sm mt-0.5 leading-relaxed">{seg.narration}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Regenerate button */}
              <div className="flex justify-center pt-2">
                <button
                  onClick={onGenerate}
                  className="flex items-center gap-2 px-5 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg text-sm transition"
                >
                  <Play size={14} />
                  Regenerate Video
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default VideoModal;