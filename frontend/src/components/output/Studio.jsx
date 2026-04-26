const Studio = ({
  selectedTopic,
  isSimplifying,
  isTranslating,
  onMindmap,
  onFlashcards,
  onQuiz,
  onImages,
  onVideo,
  onInsights,
  onDoubt,
  imagesData,   // ← NEW: passed from Output.jsx to control video button
}) => {
  const enabled = selectedTopic && !isSimplifying && !isTranslating;
  const videoEnabled = enabled && imagesData?.length > 0;

  const buttons = [
    { label: "Mind Map",       emoji: "🗺️", color: "bg-purple-600 hover:bg-purple-700", onClick: onMindmap,    active: enabled },
    { label: "Flashcards",     emoji: "🗂️", color: "bg-green-600 hover:bg-green-700",  onClick: onFlashcards, active: enabled },
    { label: "Quiz",           emoji: "🎮", color: "bg-yellow-600 hover:bg-yellow-700", onClick: onQuiz,       active: enabled },
    { label: "Key Insights",   emoji: "💡", color: "bg-cyan-600 hover:bg-cyan-700",     onClick: onInsights,   active: enabled },
    { label: "Concept Images", emoji: "🖼️", color: "bg-pink-600 hover:bg-pink-700",    onClick: onImages,     active: enabled },
    { label: "Concept Video",  emoji: "🎬", color: "bg-purple-700 hover:bg-purple-800", onClick: onVideo,     active: videoEnabled },
    { label: "Doubt Solver",   emoji: "🤔", color: "bg-blue-600 hover:bg-blue-700",    onClick: onDoubt,      active: enabled },
  ];

  return (
    <aside className="w-full lg:w-1/4 bg-gray-800 rounded-xl shadow-md p-4 max-h-[calc(100vh-180px)] overflow-y-auto">
      <h2 className="text-lg font-semibold mb-4 text-green-400 border-b border-gray-700 pb-2">Studio</h2>
      <div className="space-y-3">
        {buttons.map(({ label, emoji, color, onClick, active }) => (
          <button
            key={label}
            onClick={onClick}
            disabled={!active}
            title={label === "Concept Video" && !videoEnabled ? "Generate Concept Images first" : undefined}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition ${
              active ? `${color} text-white` : "bg-gray-700 text-gray-500 cursor-not-allowed"
            }`}
          >
            <span className="text-2xl">{emoji}</span>
            <span className="font-medium">{label}</span>
            {label === "Concept Video" && !videoEnabled && enabled && (
              <span className="ml-auto text-xs text-gray-400">needs images</span>
            )}
          </button>
        ))}
      </div>
    </aside>
  );
};

export default Studio;