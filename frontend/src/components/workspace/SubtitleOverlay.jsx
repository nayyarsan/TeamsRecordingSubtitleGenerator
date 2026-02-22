export default function SubtitleOverlay({ subtitle }) {
  if (!subtitle) return null

  return (
    <div className="absolute bottom-12 left-0 right-0 flex justify-center pointer-events-none">
      <div className="bg-black/70 rounded px-4 py-2 max-w-lg text-center">
        {subtitle.speaker && (
          <span className="text-primary font-semibold text-sm">{subtitle.speaker}: </span>
        )}
        <span className="text-white text-sm">{subtitle.text}</span>
      </div>
    </div>
  )
}
