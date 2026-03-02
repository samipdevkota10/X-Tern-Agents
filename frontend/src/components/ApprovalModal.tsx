/**
 * Approval Modal Component (HITL - Human In The Loop)
 */
import { useState } from 'react';

interface ApprovalModalProps {
  caseName: string;
  onClose: () => void;
  onSubmit: (decision: string, reason: string, approved: boolean) => void;
}

export function ApprovalModal({ caseName, onClose, onSubmit }: ApprovalModalProps) {
  const [decision, setDecision] = useState('');
  const [reason, setReason] = useState('');
  const [approved, setApproved] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!decision.trim()) return;

    setSubmitting(true);
    try {
      await onSubmit(decision, reason, approved);
    } finally {
      setSubmitting(false);
    }
  };

  const quickDecisions = [
    { label: 'Approve', value: 'Approved' },
    { label: 'Reject', value: 'Rejected' },
    { label: 'Request More Info', value: 'Additional information requested' },
    { label: 'Escalate', value: 'Escalated to senior reviewer' },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content approval-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add Decision</h2>
          <p className="case-reference">Case: {caseName}</p>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="quick-actions">
            <label>Quick Actions</label>
            <div className="quick-buttons">
              {quickDecisions.map((qd) => (
                <button
                  key={qd.value}
                  type="button"
                  className={`quick-btn ${decision === qd.value ? 'active' : ''}`}
                  onClick={() => setDecision(qd.value)}
                >
                  {qd.label}
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="decision">Decision *</label>
            <input
              type="text"
              id="decision"
              value={decision}
              onChange={(e) => setDecision(e.target.value)}
              placeholder="Enter your decision"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="reason">Reason / Justification</label>
            <textarea
              id="reason"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Provide reasoning for your decision..."
              rows={4}
            />
          </div>

          <div className="form-group approval-toggle">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={approved}
                onChange={(e) => setApproved(e.target.checked)}
              />
              <span className="checkmark"></span>
              Mark as Approved
            </label>
            <p className="help-text">
              Check this box if this is a final approval decision.
            </p>
          </div>

          <div className="modal-actions">
            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={!decision.trim() || submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Decision'}
            </button>
          </div>
        </form>

        <div className="hitl-notice">
          <span className="notice-icon">👤</span>
          <span>Human-in-the-loop verification required</span>
        </div>
      </div>
    </div>
  );
}

export default ApprovalModal;
