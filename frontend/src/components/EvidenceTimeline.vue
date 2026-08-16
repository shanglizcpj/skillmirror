<script setup lang="ts">
import {
  computed,
  onBeforeUnmount,
  onMounted,
  ref,
  watch,
} from "vue";
import axios from "axios";

import {
  historyApi,
  type EvidenceHistoryItem,
} from "../api/history";

import {
  reportApi,
  type AssessmentHistoryItem,
} from "../api/report";

interface TimelineSession {
  session_id: string;
  challenge_id: string;
  target_skill?: string;
  target_subskill?: string;
  difficulty?: string;
  previous_score?: number | null;
  new_score?: number | null;
  confidence_percent?: number | null;
  score_status?: string;
  created_at?: string;
  evidence: EvidenceHistoryItem[];
}

const props = defineProps<{
  userId: string;
}>();

const sessions = ref<TimelineSession[]>([]);
const loading = ref(false);
const errorMessage = ref("");

let reloadTimer: number | undefined;

const totalTimelineEvidence = computed(() => {
  return sessions.value.reduce(
    (total, session) =>
      total + session.evidence.length,
    0,
  );
});

function findPreviousScore(
  history: AssessmentHistoryItem[],
  currentIndex: number,
  targetSkill: string | undefined,
): number | null {
  if (!targetSkill) {
    return null;
  }

  for (
    let index = currentIndex - 1;
    index >= 0;
    index -= 1
  ) {
    const item = history[index];

    if (
      item.target_skill === targetSkill &&
      typeof item.score === "number"
    ) {
      return item.score;
    }
  }

  return null;
}

async function loadTimeline(): Promise<void> {
  const cleanedUserId = props.userId.trim();

  if (!cleanedUserId) {
    sessions.value = [];
    return;
  }

  loading.value = true;
  errorMessage.value = "";

  try {
    const [evidenceResponse, reportResponse] =
      await Promise.all([
        historyApi.getEvidence(cleanedUserId),
        reportApi.getReport(cleanedUserId),
      ]);

    const ascendingHistory = [
      ...reportResponse.history,
    ];

    const timeline = ascendingHistory.map(
      (
        item,
        index,
      ): TimelineSession => {
        const sessionEvidence =
          evidenceResponse.items.filter(
            (evidence) =>
              evidence.session_id === item.session_id,
          );

        return {
          session_id: item.session_id,
          challenge_id: item.challenge_id,
          target_skill: item.target_skill,
          target_subskill: item.target_subskill,
          difficulty: item.difficulty,
          previous_score: findPreviousScore(
            ascendingHistory,
            index,
            item.target_skill,
          ),
          new_score: item.score,
          confidence_percent:
            item.confidence_percent,
          score_status: item.score_status,
          created_at: item.created_at,
          evidence: sessionEvidence,
        };
      },
    );

    sessions.value = timeline.reverse();
  } catch (error) {
    if (axios.isAxiosError(error)) {
      const detail = error.response?.data?.detail;

      errorMessage.value =
        typeof detail === "string"
          ? detail
          : error.message;
    } else if (error instanceof Error) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value =
        "Unable to load evidence timeline.";
    }
  } finally {
    loading.value = false;
  }
}

function displayName(value: string | undefined): string {
  if (!value) {
    return "Unknown";
  }

  return value
    .replaceAll("_", " ")
    .replace(/\b\w/g, (character) =>
      character.toUpperCase(),
    );
}

function scoreText(value: unknown): string {
  return typeof value === "number"
    ? value.toFixed(1)
    : "?";
}

function confidenceText(value: unknown): string {
  if (typeof value !== "number") {
    return "—";
  }

  return `${value.toFixed(1)}%`;
}

function reliabilityText(value: unknown): string {
  if (typeof value !== "number") {
    return "—";
  }

  const percent = value <= 1 ? value * 100 : value;
  return `${percent.toFixed(0)}%`;
}

function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) {
    return "Unknown date";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function evidenceIcon(
  evidence: EvidenceHistoryItem,
): string {
  if (evidence.direction === "positive") {
    return "✓";
  }

  if (evidence.direction === "negative") {
    return "×";
  }

  if (evidence.direction === "dependency") {
    return "△";
  }

  return "•";
}

function evidenceClass(
  evidence: EvidenceHistoryItem,
): string {
  if (evidence.direction === "positive") {
    return "positive";
  }

  if (evidence.direction === "negative") {
    return "negative";
  }

  if (evidence.direction === "dependency") {
    return "dependency";
  }

  return "neutral";
}

function scoreChangeClass(
  session: TimelineSession,
): string {
  if (
    typeof session.previous_score !== "number" ||
    typeof session.new_score !== "number"
  ) {
    return "neutral";
  }

  if (session.new_score > session.previous_score) {
    return "positive";
  }

  if (session.new_score < session.previous_score) {
    return "negative";
  }

  return "neutral";
}

watch(
  () => props.userId,
  () => {
    if (reloadTimer !== undefined) {
      window.clearTimeout(reloadTimer);
    }

    reloadTimer = window.setTimeout(() => {
      void loadTimeline();
    }, 500);
  },
);

onMounted(() => {
  void loadTimeline();
});

onBeforeUnmount(() => {
  if (reloadTimer !== undefined) {
    window.clearTimeout(reloadTimer);
  }
});
</script>

<template>
  <section class="timeline-card">
    <div class="timeline-heading">
      <div>
        <p class="section-label">EVIDENCE TIMELINE</p>
        <h2>Verified Skill Changes</h2>

        <p>
          Each event links a completed challenge to its
          materialized evidence and resulting skill update.
        </p>
      </div>

      <div class="timeline-summary">
        <span>
          Sessions
          <strong>{{ sessions.length }}</strong>
        </span>

        <span>
          Evidence
          <strong>{{ totalTimelineEvidence }}</strong>
        </span>

        <button
          type="button"
          :disabled="loading"
          @click="loadTimeline"
        >
          {{ loading ? "Loading..." : "Refresh Timeline" }}
        </button>
      </div>
    </div>

    <div
      v-if="errorMessage"
      class="error-message"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="loading && !sessions.length"
      class="empty-state"
    >
      Loading evidence timeline...
    </div>

    <div
      v-else-if="!sessions.length"
      class="empty-state"
    >
      No completed assessment sessions were found.
    </div>

    <div v-else class="timeline">
      <article
        v-for="session in sessions"
        :key="session.session_id"
        class="timeline-event"
      >
        <div class="timeline-marker">
          <span></span>
        </div>

        <div class="event-card">
          <div class="event-heading">
            <div>
              <time>
                {{ formatDate(session.created_at) }}
              </time>

              <div class="title-row">
                <h3>
                  {{
                    displayName(
                      session.target_skill,
                    )
                  }}
                </h3>

                <span class="verified-badge">
                  VERIFIED
                </span>
              </div>

              <p>
                {{
                  displayName(
                    session.target_subskill,
                  )
                }}
              </p>
            </div>

            <div
              class="score-change"
              :class="scoreChangeClass(session)"
            >
              <span>Skill Score</span>

              <strong>
                {{ scoreText(session.previous_score) }}
                <span class="arrow">→</span>
                {{ scoreText(session.new_score) }}
              </strong>
            </div>
          </div>

          <div class="event-meta">
            <span>
              Challenge
              <strong>{{ session.challenge_id }}</strong>
            </span>

            <span>
              Difficulty
              <strong>
                {{ session.difficulty || "—" }}
              </strong>
            </span>

            <span>
              Confidence
              <strong>
                {{
                  confidenceText(
                    session.confidence_percent,
                  )
                }}
              </strong>
            </span>

            <span>
              Status
              <strong>
                {{ session.score_status || "—" }}
              </strong>
            </span>
          </div>

          <div class="evidence-section">
            <h4>
              Evidence generated
              <span>
                {{ session.evidence.length }}
              </span>
            </h4>

            <p
              v-if="!session.evidence.length"
              class="no-evidence"
            >
              No browser-visible Evidence was associated
              with this session.
            </p>

            <div v-else class="evidence-rows">
              <div
                v-for="(
                  evidence,
                  index
                ) in session.evidence"
                :key="
                  evidence.evidence_id || index
                "
                class="evidence-row"
              >
                <span
                  class="evidence-icon"
                  :class="evidenceClass(evidence)"
                >
                  {{ evidenceIcon(evidence) }}
                </span>

                <div class="evidence-description">
                  <strong>
                    {{
                      displayName(
                        evidence.sub_skill ||
                        evidence.subskill ||
                        evidence.skill,
                      )
                    }}
                  </strong>

                  <p>
                    {{
                      evidence.reason ||
                      "Verified evidence record."
                    }}
                  </p>
                </div>

                <div class="evidence-values">
                  <span>
                    Performance
                    <strong>
                      {{
                        scoreText(
                          evidence.performance_score,
                        )
                      }}
                    </strong>
                  </span>

                  <span>
                    Reliability
                    <strong>
                      {{
                        reliabilityText(
                          evidence.reliability,
                        )
                      }}
                    </strong>
                  </span>
                </div>
              </div>
            </div>
          </div>

          <footer class="event-footer">
            <code>{{ session.session_id }}</code>

            <span>
              {{
                session.evidence.length
              }}
              trusted evidence records
            </span>
          </footer>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.timeline-card {
  margin-bottom: 18px;
  padding: 28px;
  border: 1px solid #e0e6ef;
  border-radius: 18px;
  background: white;
  box-shadow: 0 14px 38px rgb(31 50 81 / 7%);
}

.timeline-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.section-label {
  margin: 0 0 8px;
  color: #3867ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.timeline-heading h2 {
  margin: 0;
  color: #14213d;
  font-size: 25px;
}

.timeline-heading p {
  max-width: 720px;
  margin: 9px 0 0;
  color: #7d879b;
}

.timeline-summary {
  display: flex;
  align-items: center;
  gap: 18px;
}

.timeline-summary > span {
  color: #8792a6;
  font-size: 11px;
}

.timeline-summary strong {
  display: block;
  margin-top: 4px;
  color: #14213d;
  font-size: 18px;
}

.timeline-summary button {
  min-height: 42px;
  padding: 0 16px;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  background: white;
  color: #26344d;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.timeline-summary button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.error-message {
  margin-bottom: 18px;
  padding: 13px 16px;
  border: 1px solid #fecaca;
  border-radius: 10px;
  background: #fff1f2;
  color: #b42318;
}

.empty-state {
  padding: 55px 20px;
  color: #7d879b;
  text-align: center;
}

.timeline {
  position: relative;
}

.timeline::before {
  position: absolute;
  top: 14px;
  bottom: 14px;
  left: 11px;
  width: 2px;
  background: #dfe5ef;
  content: "";
}

.timeline-event {
  position: relative;
  display: grid;
  grid-template-columns: 24px 1fr;
  gap: 18px;
  margin-bottom: 18px;
}

.timeline-event:last-child {
  margin-bottom: 0;
}

.timeline-marker {
  position: relative;
  z-index: 1;
  padding-top: 25px;
}

.timeline-marker span {
  display: block;
  width: 22px;
  height: 22px;
  border: 5px solid #e9efff;
  border-radius: 50%;
  background: #3867ff;
  box-sizing: border-box;
}

.event-card {
  padding: 21px;
  border: 1px solid #e3e8f1;
  border-radius: 14px;
  background: #fcfdff;
}

.event-heading {
  display: flex;
  justify-content: space-between;
  gap: 24px;
}

.event-heading time {
  color: #8a95a9;
  font-size: 11px;
}

.title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 5px;
}

.title-row h3 {
  margin: 0;
  color: #14213d;
  font-size: 21px;
}

.verified-badge {
  padding: 5px 8px;
  border-radius: 99px;
  background: #dcfce7;
  color: #15803d;
  font-size: 9px;
  font-weight: 800;
}

.event-heading p {
  margin: 5px 0 0;
  color: #7d879b;
  font-size: 13px;
}

.score-change {
  text-align: right;
}

.score-change > span {
  display: block;
  color: #8792a6;
  font-size: 11px;
}

.score-change > strong {
  color: #26344d;
  font-size: 25px;
}

.score-change.positive > strong {
  color: #16845f;
}

.score-change.negative > strong {
  color: #c2414b;
}

.arrow {
  margin: 0 7px;
  color: #9aa4b6;
}

.event-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 9px;
  margin: 19px 0;
}

.event-meta > span {
  padding: 11px;
  border-radius: 9px;
  background: #f4f7fb;
  color: #8792a6;
  font-size: 10px;
}

.event-meta strong {
  display: block;
  margin-top: 5px;
  color: #26344d;
  font-size: 12px;
}

.evidence-section {
  padding-top: 17px;
  border-top: 1px solid #e5e9f1;
}

.evidence-section h4 {
  margin: 0 0 12px;
  color: #26344d;
  font-size: 14px;
}

.evidence-section h4 span {
  margin-left: 5px;
  color: #8792a6;
}

.no-evidence {
  color: #8792a6;
  font-size: 12px;
}

.evidence-rows {
  display: grid;
  gap: 9px;
}

.evidence-row {
  display: grid;
  grid-template-columns: 30px 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 10px;
  background: #f6f8fc;
}

.evidence-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #eef1f5;
  color: #667085;
  font-weight: 800;
  line-height: 28px;
  text-align: center;
}

.evidence-icon.positive {
  background: #dcfce7;
  color: #15803d;
}

.evidence-icon.negative {
  background: #ffe4e6;
  color: #be123c;
}

.evidence-icon.dependency {
  background: #fff3cd;
  color: #9a6700;
}

.evidence-description strong {
  color: #26344d;
  font-size: 13px;
}

.evidence-description p {
  margin: 3px 0 0;
  color: #6f7b90;
  font-size: 12px;
}

.evidence-values {
  display: flex;
  gap: 18px;
  text-align: right;
}

.evidence-values > span {
  color: #8792a6;
  font-size: 9px;
}

.evidence-values strong {
  display: block;
  margin-top: 3px;
  color: #26344d;
  font-size: 12px;
}

.event-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 14px;
  padding-top: 13px;
  border-top: 1px solid #e5e9f1;
  color: #8792a6;
  font-size: 10px;
}

.event-footer code {
  color: #3867ff;
}

@media (max-width: 850px) {
  .timeline-heading,
  .event-heading {
    align-items: flex-start;
    flex-direction: column;
  }

  .score-change {
    text-align: left;
  }

  .event-meta {
    grid-template-columns: repeat(2, 1fr);
  }

  .evidence-row {
    grid-template-columns: 30px 1fr;
  }

  .evidence-values {
    grid-column: 2;
    justify-content: flex-start;
    text-align: left;
  }
}

@media (max-width: 600px) {
  .timeline-card {
    padding: 18px;
  }

  .timeline-summary {
    align-items: stretch;
    flex-direction: column;
  }

  .event-meta {
    grid-template-columns: 1fr;
  }

  .event-footer {
    align-items: flex-start;
    flex-direction: column;
    gap: 6px;
  }
}
</style>