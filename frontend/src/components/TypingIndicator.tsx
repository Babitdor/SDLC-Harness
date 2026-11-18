export default function TypingIndicator() {
  return (
    <div className="mb-6 animate-message-in">
      <div className="annotation-rule is-orchestrator">
        <div className="flex items-center gap-3 py-1">
          <span className="label-mono text-blue-400/80">ORCHESTRATOR</span>
          <div className="flex items-center gap-1.5 ml-2">
            <div className="w-1 h-1 bg-blue-400 rounded-full typing-dot" />
            <div className="w-1 h-1 bg-blue-400 rounded-full typing-dot" />
            <div className="w-1 h-1 bg-blue-400 rounded-full typing-dot" />
          </div>
        </div>
      </div>
    </div>
  );
}
