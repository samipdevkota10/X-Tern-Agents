/**
 * Case List Page
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { Case } from '../types';

export function CaseListPage() {
  const navigate = useNavigate();
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);

  useEffect(() => {
    loadCases();
  }, []);

  const loadCases = async () => {
    try {
      setLoading(true);
      const response = await apiClient.listCases();
      setCases(response.cases);
      setError(null);
    } catch (err) {
      setError('Failed to load cases. Is the backend running?');
      console.error('Error loading cases:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateCase = async (title: string, description: string, priority: string) => {
    try {
      const newCase = await apiClient.createCase({ title, description, priority });
      setCases([newCase, ...cases]);
      setCreateModalOpen(false);
    } catch (err) {
      console.error('Error creating case:', err);
    }
  };

  const getPriorityClass = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'high':
        return 'priority-high';
      case 'low':
        return 'priority-low';
      default:
        return 'priority-normal';
    }
  };

  const getStatusClass = (status: string) => {
    switch (status.toLowerCase()) {
      case 'open':
        return 'status-open';
      case 'closed':
        return 'status-closed';
      case 'pending':
        return 'status-pending';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <div className="case-list-page">
        <div className="loading">Loading cases...</div>
      </div>
    );
  }

  return (
    <div className="case-list-page">
      <header className="page-header">
        <h1>Cases</h1>
        <button className="btn-primary" onClick={() => setCreateModalOpen(true)}>
          + New Case
        </button>
      </header>

      {error && <div className="error-message">{error}</div>}

      <div className="case-list">
        {cases.length === 0 ? (
          <div className="empty-state">
            <p>No cases found. Create your first case to get started.</p>
          </div>
        ) : (
          <table className="cases-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Decisions</th>
                <th>Created</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((caseItem) => (
                <tr
                  key={caseItem.id}
                  onClick={() => navigate(`/cases/${caseItem.id}`)}
                  className="case-row"
                >
                  <td>{caseItem.title}</td>
                  <td>
                    <span className={`priority-badge ${getPriorityClass(caseItem.priority)}`}>
                      {caseItem.priority}
                    </span>
                  </td>
                  <td>
                    <span className={`status-badge ${getStatusClass(caseItem.status)}`}>
                      {caseItem.status}
                    </span>
                  </td>
                  <td>{caseItem.decisions.length}</td>
                  <td>{new Date(caseItem.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {createModalOpen && (
        <CreateCaseModal
          onClose={() => setCreateModalOpen(false)}
          onCreate={handleCreateCase}
        />
      )}
    </div>
  );
}

interface CreateCaseModalProps {
  onClose: () => void;
  onCreate: (title: string, description: string, priority: string) => void;
}

function CreateCaseModal({ onClose, onCreate }: CreateCaseModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState('normal');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (title && description) {
      onCreate(title, description, priority);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <h2>Create New Case</h2>
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="title">Title</label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Case title"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Case description"
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="priority">Priority</label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
            >
              <option value="low">Low</option>
              <option value="normal">Normal</option>
              <option value="high">High</option>
            </select>
          </div>
          <div className="modal-actions">
            <button type="button" className="btn-secondary" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-primary">
              Create
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default CaseListPage;
