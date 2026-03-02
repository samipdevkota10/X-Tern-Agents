/**
 * Case Detail Page with Timeline
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Case, Decision, RiskScore } from '../types';
import { ApprovalModal } from '../components/ApprovalModal';

export function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [riskScore, setRiskScore] = useState<RiskScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvalModalOpen, setApprovalModalOpen] = useState(false);

  useEffect(() => {
    if (id) {
      loadCase(id);
    }
  }, [id]);

  const loadCase = async (caseId: string) => {
    try {
      setLoading(true);
      const data = await apiClient.getCase(caseId);
      setCaseData(data);
      
      // Also compute risk score
      const risk = await apiClient.computeRiskScore(caseId, {
        priority: data.priority,
      });
      setRiskScore(risk);
      
      setError(null);
    } catch (err) {
      setError('Failed to load case details');
      console.error('Error loading case:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleApproval = async (decision: string, reason: string, approved: boolean) => {
    if (!id) return;
    
    try {
      const updatedCase = await apiClient.appendDecision(id, {
        decision,
        made_by: 'current_user@example.com', // In production, get from auth context
        reason,
        approved,
      });
      setCaseData(updatedCase);
      setApprovalModalOpen(false);
    } catch (err) {
      console.error('Error adding decision:', err);
    }
  };

  const getRiskLevelClass = (level: string) => {
    switch (level.toLowerCase()) {
      case 'critical':
        return 'risk-critical';
      case 'high':
        return 'risk-high';
      case 'medium':
        return 'risk-medium';
      default:
        return 'risk-low';
    }
  };

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="case-detail-page">
        <div className="loading">Loading case details...</div>
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="case-detail-page">
        <div className="error-message">{error || 'Case not found'}</div>
        <button className="btn-secondary" onClick={() => navigate('/cases')}>
          Back to Cases
        </button>
      </div>
    );
  }

  return (
    <div className="case-detail-page">
      <header className="page-header">
        <button className="btn-back" onClick={() => navigate('/cases')}>
          ← Back
        </button>
        <h1>{caseData.title}</h1>
        <button className="btn-primary" onClick={() => setApprovalModalOpen(true)}>
          Add Decision
        </button>
      </header>

      <div className="case-content">
        <section className="case-info">
          <h2>Case Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <label>ID</label>
              <span>{caseData.id}</span>
            </div>
            <div className="info-item">
              <label>Status</label>
              <span className={`status-badge status-${caseData.status}`}>
                {caseData.status}
              </span>
            </div>
            <div className="info-item">
              <label>Priority</label>
              <span className={`priority-badge priority-${caseData.priority}`}>
                {caseData.priority}
              </span>
            </div>
            <div className="info-item">
              <label>Created</label>
              <span>{formatTimestamp(caseData.created_at)}</span>
            </div>
            <div className="info-item">
              <label>Updated</label>
              <span>{formatTimestamp(caseData.updated_at)}</span>
            </div>
          </div>
          <div className="description">
            <label>Description</label>
            <p>{caseData.description}</p>
          </div>
        </section>

        {riskScore && (
          <section className="risk-assessment">
            <h2>Risk Assessment</h2>
            <div className="risk-score-display">
              <div className={`risk-level ${getRiskLevelClass(riskScore.risk_level)}`}>
                <span className="score">{(riskScore.risk_score * 100).toFixed(0)}%</span>
                <span className="level">{riskScore.risk_level.toUpperCase()}</span>
              </div>
              <div className="risk-details">
                <div className="factors">
                  <h4>Factors Evaluated</h4>
                  <ul>
                    {riskScore.factors_evaluated.map((factor) => (
                      <li key={factor}>{factor}</li>
                    ))}
                  </ul>
                </div>
                <div className="recommendations">
                  <h4>Recommendations</h4>
                  <ul>
                    {riskScore.recommendations.map((rec, idx) => (
                      <li key={idx}>{rec}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </section>
        )}

        <section className="decision-timeline">
          <h2>Decision Timeline</h2>
          {caseData.decisions.length === 0 ? (
            <div className="empty-timeline">
              <p>No decisions have been made yet.</p>
            </div>
          ) : (
            <div className="timeline">
              {caseData.decisions.map((decision: Decision, index: number) => (
                <div key={decision.id} className="timeline-item">
                  <div className="timeline-marker">
                    <span className={decision.approved ? 'approved' : 'pending'}>
                      {decision.approved ? '✓' : '○'}
                    </span>
                  </div>
                  <div className="timeline-content">
                    <div className="timeline-header">
                      <span className="decision-number">Decision #{index + 1}</span>
                      <span className="timestamp">{formatTimestamp(decision.timestamp)}</span>
                    </div>
                    <div className="decision-text">{decision.decision}</div>
                    {decision.reason && (
                      <div className="decision-reason">
                        <strong>Reason:</strong> {decision.reason}
                      </div>
                    )}
                    <div className="decision-meta">
                      <span className="made-by">By: {decision.made_by}</span>
                      <span className={`approval-status ${decision.approved ? 'approved' : 'not-approved'}`}>
                        {decision.approved ? 'Approved' : 'Not Approved'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </div>

      {approvalModalOpen && (
        <ApprovalModal
          caseName={caseData.title}
          onClose={() => setApprovalModalOpen(false)}
          onSubmit={handleApproval}
        />
      )}
    </div>
  );
}

export default CaseDetailPage;
