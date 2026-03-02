/**
 * API Client for X-Tern Agents Backend
 */
import axios, { AxiosInstance, AxiosError } from 'axios';
import {
  Case,
  CaseCreate,
  CaseListResponse,
  DecisionCreate,
  HealthResponse,
  RiskScore,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_TIMEOUT = parseInt(import.meta.env.VITE_API_TIMEOUT || '30000');

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: API_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        console.error('API Error:', error.message);
        return Promise.reject(error);
      }
    );
  }

  // Health
  async getHealth(): Promise<HealthResponse> {
    const response = await this.client.get<HealthResponse>('/health');
    return response.data;
  }

  // Cases
  async createCase(data: CaseCreate): Promise<Case> {
    const response = await this.client.post<Case>('/cases', data);
    return response.data;
  }

  async listCases(
    page: number = 1,
    pageSize: number = 10,
    statusFilter?: string
  ): Promise<CaseListResponse> {
    const params: Record<string, string | number> = { page, page_size: pageSize };
    if (statusFilter) {
      params.status_filter = statusFilter;
    }
    const response = await this.client.get<CaseListResponse>('/cases', { params });
    return response.data;
  }

  async getCase(caseId: string): Promise<Case> {
    const response = await this.client.get<Case>(`/cases/${caseId}`);
    return response.data;
  }

  async appendDecision(caseId: string, data: DecisionCreate): Promise<Case> {
    const response = await this.client.post<Case>(`/cases/${caseId}/decisions`, data);
    return response.data;
  }

  // MCP Tools
  async computeRiskScore(
    caseId?: string,
    factors?: Record<string, unknown>
  ): Promise<RiskScore> {
    const response = await this.client.post<RiskScore>('/mcp/tools/compute_risk_score', {
      case_id: caseId,
      factors: factors || {},
    });
    return response.data;
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
export default apiClient;
