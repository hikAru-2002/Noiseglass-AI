export default function EmptyState({ onRun, disabled }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon">◇</div>
      <p className="empty-state-text">
        Nothing's been sorted yet. Run analysis to turn raw tickets into
        ranked, actionable signal.
      </p>
      <button className="run-btn run-btn-empty" onClick={onRun} disabled={disabled}>
        Run analysis
      </button>
    </div>
  )
}
