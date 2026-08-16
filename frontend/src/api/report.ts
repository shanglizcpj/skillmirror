import axios from "axios";

export interface ReportScore {
  algorithm_version?: string;
  calculation_id?: string;
  skill_id?: string;
  previous_score?: number | null;
  new_score?: number;
  score_status?: string;
  evidence_weight?: number;
  evidence_score?: number;
  formula?: string;
  reason?: string;

  [key: string]: unknown;
}

export interface ReportConfidence {
  algorithm_version?: string;
  confidence?: number;
  confidence_percent?: number;
  confidence_status?: string;
  reason?: string;

  [key: string]: unknown;
}

export interface SubskillState {
  id?: string;
  sub_skill_id?: string;
  score?: number | null;
  confidence?: number;

  [key: string]: unknown;
}

export interface SkillState {
  skill_id?: string;
  id?: string;
  score?: number | null;
  confidence?: number;
  evidence_count?: number;
  subskills?: SubskillState[];

  [key: string]: unknown;
}

export interface SkillMirror {
  user_id?: string;
  skills?: SkillState[];

  [key: string]: unknown;
}

export interface NextExaminer {
  target_skill?: string;
  target_subskill?: string;
  difficulty?: string;
  challenge_type?: string;
  mode?: string;
  reason?: string;
  decision_source?: string;

  [key: string]: unknown;
}

export interface EvidenceSummary {
  accepted_count: number;
  rejected_count: number;
}

export interface TrustSummary {
  rejected_b_records_count: number;
  rejected_history_count: number;
  replayed_evidence_count: number;
  caller_verification_status_trusted: boolean;
}

export interface LatestAssessment {
  session_id: string;
  challenge_id: string;
  created_at: string;
  score: ReportScore;
  confidence: ReportConfidence;
  skill_mirror: SkillMirror;
  next_examiner: NextExaminer;
  evidence_summary: EvidenceSummary;
  trust_summary: TrustSummary;
}

export interface AssessmentHistoryItem {
  session_id: string;
  challenge_id: string;
  target_skill?: string;
  target_subskill?: string;
  difficulty?: string;
  score?: number | null;
  confidence_percent?: number | null;
  score_status?: string;
  created_at?: string;
}

export interface AssessmentReportResponse {
  user_id: string;
  total_assessments: number;
  latest: LatestAssessment | null;
  history: AssessmentHistoryItem[];
}

const api = axios.create({
  baseURL: "/api",
  timeout: 20000,
  headers: {
    Accept: "application/json",
  },
});

export const reportApi = {
  async getReport(
    userId: string,
  ): Promise<AssessmentReportResponse> {
    const response =
      await api.get<AssessmentReportResponse>(
        `/agent/history/${encodeURIComponent(userId)}/report`,
      );

    return response.data;
  },
};