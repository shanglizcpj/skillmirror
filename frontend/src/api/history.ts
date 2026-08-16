import axios from "axios";

export interface EvidenceHistoryItem {
  evidence_id?: string;
  user_id?: string;
  session_id?: string;
  challenge_id?: string;
  challenge_digest?: string;
  challenge_type?: string;
  skill?: string;
  sub_skill?: string;
  subskill?: string;
  performance_score?: number;
  score_delta?: number;
  strength?: string;
  difficulty?: string;
  reliability?: number;
  direction?: string;
  reason?: string;
  rule_id?: string;
  rule_version?: string;
  timestamp?: string;
  created_at?: string;

  [key: string]: unknown;
}

export interface ChallengeHistoryItem {
  session_id?: string;
  challenge_id?: string;
  challenge_digest?: string;
  challenge_type?: string;
  target_skill?: string;
  target_subskill?: string;
  difficulty?: string;
  score?: number;
  confidence?: number;
  completed_at?: string;
  timestamp?: string;

  [key: string]: unknown;
}

export interface HistoryResponse<T> {
  user_id: string;
  total: number;
  items: T[];
}

const api = axios.create({
  baseURL: "/api",
  timeout: 20000,
  headers: {
    Accept: "application/json",
  },
});

export const historyApi = {
  async getEvidence(
    userId: string,
  ): Promise<HistoryResponse<EvidenceHistoryItem>> {
    const response = await api.get<
      HistoryResponse<EvidenceHistoryItem>
    >(
      `/agent/history/${encodeURIComponent(userId)}/evidence`,
    );

    return response.data;
  },

  async getChallenges(
    userId: string,
  ): Promise<HistoryResponse<ChallengeHistoryItem>> {
    const response = await api.get<
      HistoryResponse<ChallengeHistoryItem>
    >(
      `/agent/history/${encodeURIComponent(userId)}/challenges`,
    );

    return response.data;
  },
};