import axios from "axios";

export interface StartChallengeRequest {
  user_id: string;
  session_id: string;
}

export interface PublicTestCase {
  case_id: string;
  visibility: "public";
  args: unknown[];
  kwargs: Record<string, unknown>;
  expected?: unknown;
  expected_exception?: string;
}

export interface LearnerChallenge {
  schema_version?: string;
  challenge_id: string;
  target_skill?: string;
  target_subskill?: string;
  difficulty?: string;
  challenge_type?: string;
  title?: string;
  task_description?: string;
  entry_point?: string;
  starter_code?: string;
  generation_source?: string;
  content_hash?: string;
  public_tests?: PublicTestCase[];

  [key: string]: unknown;
}

export interface StartChallengeResponse {
  user_id: string;
  session_id: string;
  examiner_decision?: Record<string, unknown>;

  // 兼容后端可能使用的两种字段名
  challenge?: LearnerChallenge;
  learner_challenge?: LearnerChallenge;

  [key: string]: unknown;
}

export interface RunTestsRequest {
  user_id: string;
  session_id: string;
  code: string;
  timeout_seconds: number;
}

export interface RunTestsResponse {
  status: string;
  challenge_id: string;
  challenge_digest: string;
  passed: number;
  total: number;
  public_passed: number;
  public_total: number;
  hidden_passed: number;
  hidden_total: number;
  failed_cases: Array<Record<string, unknown>>;
  runtime: number;
  sandbox_mode: string;
}

export interface HintRequest {
  user_id: string;
  session_id: string;
  user_code: string;
  failed_attempts: number;
  asked_for_hint: boolean;
}

export interface HintResponse {
  action: string;
  hint_level?: number | null;
  hint_key?: string | null;
  message?: string | null;
  source?: string | null;
  reason?: string | null;
}

export interface CompleteAssessmentRequest {
  user_id: string;
  session_id: string;
  submitted_code: string;
  elapsed_seconds?: number;
}

export interface ScoreResult {
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

export interface ConfidenceResult {
  algorithm_version?: string;
  confidence?: number;
  confidence_percent?: number;
  confidence_status?: string;
  formula?: string;
  reason?: string;

  [key: string]: unknown;
}

export interface CompleteAssessmentResponse {
  status?: string;
  score?: ScoreResult;
  confidence?: ConfidenceResult;
  updated_skill_mirror?: Record<string, unknown>;
  next_examiner?: Record<string, unknown>;
  trust_report?: Record<string, unknown>;

  [key: string]: unknown;
}

const api = axios.create({
  baseURL: "/api",
  timeout: 12000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const challengeApi = {
  async start(
    payload: StartChallengeRequest,
  ): Promise<StartChallengeResponse> {
    const response = await api.post<StartChallengeResponse>(
      "/agent/challenges/start",
      payload,
    );

    return response.data;
  },

  async runTests(payload: RunTestsRequest): Promise<RunTestsResponse> {
    const response = await api.post<RunTestsResponse>("/tests/run", payload);
    return response.data;
  },

  async requestHint(payload: HintRequest): Promise<HintResponse> {
    const response = await api.post<HintResponse>(
      "/agent/hints/request",
      payload,
    );

    return response.data;
  },

  async completeAssessment(
    payload: CompleteAssessmentRequest,
  ): Promise<CompleteAssessmentResponse> {
    const response = await api.post<CompleteAssessmentResponse>(
      "/agent/assessments/complete",
      payload,
    );

    return response.data;
  },
};

export { getApiErrorMessage } from "./errors";