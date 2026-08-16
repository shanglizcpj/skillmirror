<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";
import axios from "axios";
import EvidenceTimeline from "../components/EvidenceTimeline.vue";

import {
  historyApi,
  type ChallengeHistoryItem,
  type EvidenceHistoryItem,
} from "../api/history";

const userId = ref(
  localStorage.getItem("skillmirror-user-id") || "U-WEB",
);

const evidenceItems = ref<EvidenceHistoryItem[]>([]);
const challengeItems = ref<ChallengeHistoryItem[]>([]);

const selectedSkill = ref("");
const loading = ref(false);
const errorMessage = ref("");

const skills = computed(() => {
  return Array.from(
    new Set(
      evidenceItems.value
        .map((item) => item.skill)
        .filter((skill): skill is string => Boolean(skill)),
    ),
  ).sort();
});

const filteredEvidence = computed(() => {
  if (!selectedSkill.value) {
    return evidenceItems.value;
  }

  return evidenceItems.value.filter(
    (item) => item.skill === selectedSkill.value,
  );
});

const averageReliability = computed(() => {
  const values = evidenceItems.value
    .map((item) => item.reliability)
    .filter(
      (value): value is number =>
        typeof value === "number" &&
        Number.isFinite(value),
    );

  if (!values.length) {
    return 0;
  }

  return (
    values.reduce((total, value) => total + value, 0) /
    values.length
  );
});

function readError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === "string") {
      return detail;
    }

    return error.message;
  }

  if (error instanceof Error) {
    return error.message;
  }

  return "Unable to load evidence history.";
}

async function loadHistory(): Promise<void> {
  const cleanedUserId = userId.value.trim();

  if (!cleanedUserId) {
    errorMessage.value = "User ID cannot be empty.";
    return;
  }

  loading.value = true;
  errorMessage.value = "";

  try {
    localStorage.setItem(
      "skillmirror-user-id",
      cleanedUserId,
    );

    const [evidenceResponse, challengeResponse] =
      await Promise.all([
        historyApi.getEvidence(cleanedUserId),
        historyApi.getChallenges(cleanedUserId),
      ]);

    evidenceItems.value = evidenceResponse.items;
    challengeItems.value = challengeResponse.items;
  } catch (error) {
    errorMessage.value = readError(error);
  } finally {
    loading.value = false;
  }
}

function formatScore(value: unknown): string {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  return value.toFixed(1);
}

function formatReliability(value: unknown): string {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value)
  ) {
    return "—";
  }

  const percent = value <= 1 ? value * 100 : value;
  return `${percent.toFixed(0)}%`;
}

function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) {
    return "—";
  }

  const parsed = new Date(value);

  if (Number.isNaN(parsed.getTime())) {
    return value;
  }

  return parsed.toLocaleString();
}

function strengthClass(value: unknown): string {
  if (typeof value !== "string") {
    return "unknown";
  }

  return value.toLowerCase().replaceAll(" ", "-");
}

onMounted(() => {
  void loadHistory();
});
</script>

<template>
  <main class="evidence-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">VERIFIED RECORDS</p>
        <h1>Evidence History</h1>
        <p class="subtitle">
          Evidence shown here was materialized and verified by
          the trusted assessment pipeline.
        </p>
      </div>

      <div class="user-controls">
        <label for="evidence-user-id">User ID</label>

        <div class="control-row">
          <input
            id="evidence-user-id"
            v-model="userId"
            type="text"
            :disabled="loading"
            @keyup.enter="loadHistory"
          />

          <button
            type="button"
            :disabled="loading"
            @click="loadHistory"
          >
            {{ loading ? "Loading..." : "Refresh" }}
          </button>
        </div>
      </div>
    </section>

    <div
      v-if="errorMessage"
      class="message error-message"
    >
      <strong>Unable to load history</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <section class="summary-grid">
      <article class="summary-card">
        <span>Verified Evidence</span>
        <strong>{{ evidenceItems.length }}</strong>
      </article>

      <article class="summary-card">
        <span>Completed Challenges</span>
        <strong>{{ challengeItems.length }}</strong>
      </article>

      <article class="summary-card">
        <span>Measured Skills</span>
        <strong>{{ skills.length }}</strong>
      </article>

      <article class="summary-card">
        <span>Average Reliability</span>
        <strong>
          {{ formatReliability(averageReliability) }}
        </strong>
      </article>
    </section>

    <EvidenceTimeline :user-id="userId" />
    
    <section class="content-card">
      <div class="card-heading">
        <div>
          <p class="section-label">EVIDENCE ITEMS</p>
          <h2>Trusted Evidence Records</h2>
        </div>

        <select v-model="selectedSkill">
          <option value="">All skills</option>

          <option
            v-for="skill in skills"
            :key="skill"
            :value="skill"
          >
            {{ skill }}
          </option>
        </select>
      </div>

      <div v-if="loading" class="empty-state">
        Loading evidence history...
      </div>

      <div
        v-else-if="!filteredEvidence.length"
        class="empty-state"
      >
        No verified evidence was found for this user.
      </div>

      <div v-else class="evidence-list">
        <article
          v-for="(item, index) in filteredEvidence"
          :key="item.evidence_id || index"
          class="evidence-card"
        >
          <div class="evidence-top">
            <div>
              <div class="title-row">
                <h3>
                  {{ item.skill || "Unknown skill" }}
                </h3>

                <span
                  class="strength-badge"
                  :class="strengthClass(item.strength)"
                >
                  {{ item.strength || "unknown" }}
                </span>
              </div>

              <p>
                {{
                  item.sub_skill ||
                  item.subskill ||
                  "General skill evidence"
                }}
              </p>
            </div>

            <div class="performance-score">
              <span>Performance</span>
              <strong>
                {{ formatScore(item.performance_score) }}
              </strong>
            </div>
          </div>

          <p class="reason">
            {{
              item.reason ||
              "Verified assessment evidence."
            }}
          </p>

          <div class="evidence-meta">
            <span>
              Challenge
              <strong>
                {{ item.challenge_id || "—" }}
              </strong>
            </span>

            <span>
              Difficulty
              <strong>
                {{ item.difficulty || "—" }}
              </strong>
            </span>

            <span>
              Reliability
              <strong>
                {{ formatReliability(item.reliability) }}
              </strong>
            </span>

            <span>
              Direction
              <strong>
                {{ item.direction || "—" }}
              </strong>
            </span>
          </div>

          <div class="evidence-footer">
            <code>
              {{ item.evidence_id || "No evidence ID" }}
            </code>

            <time>
              {{
                formatDate(
                  item.timestamp || item.created_at,
                )
              }}
            </time>
          </div>
        </article>
      </div>
    </section>

    <section class="content-card challenge-history">
      <div class="card-heading">
        <div>
          <p class="section-label">CHALLENGE HISTORY</p>
          <h2>Completed Sessions</h2>
        </div>

        <span class="record-count">
          {{ challengeItems.length }} records
        </span>
      </div>

      <div
        v-if="!challengeItems.length && !loading"
        class="empty-state"
      >
        No completed challenge history was found.
      </div>

      <div v-else class="history-table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Challenge</th>
              <th>Skill</th>
              <th>Subskill</th>
              <th>Difficulty</th>
              <th>Session</th>
              <th>Completed</th>
            </tr>
          </thead>

          <tbody>
            <tr
              v-for="(item, index) in challengeItems"
              :key="item.session_id || index"
            >
              <td>
                <strong>
                  {{ item.challenge_id || "—" }}
                </strong>
              </td>

              <td>{{ item.target_skill || "—" }}</td>

              <td>
                {{ item.target_subskill || "—" }}
              </td>

              <td>
                <span class="difficulty-badge">
                  {{ item.difficulty || "—" }}
                </span>
              </td>

              <td>
                <code>{{ item.session_id || "—" }}</code>
              </td>

              <td>
                {{
                  formatDate(
                    item.completed_at || item.timestamp,
                  )
                }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </main>
</template>

<style scoped>
.evidence-page {
  width: min(1460px, calc(100% - 48px));
  margin: 0 auto;
  padding: 42px 0 72px;
  color: #14213d;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 32px;
  margin-bottom: 28px;
}

.eyebrow,
.section-label {
  margin: 0 0 8px;
  color: #3867ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.page-heading h1 {
  margin: 0;
  font-size: clamp(34px, 4vw, 52px);
}

.subtitle {
  max-width: 700px;
  margin: 10px 0 0;
  color: #758098;
}

.user-controls {
  min-width: 340px;
}

.user-controls label {
  display: block;
  margin-bottom: 7px;
  color: #758098;
  font-size: 13px;
  font-weight: 700;
}

.control-row {
  display: flex;
  gap: 10px;
}

.control-row input,
.card-heading select {
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  background: white;
  color: #14213d;
  outline: none;
}

.control-row input {
  min-width: 190px;
}

.control-row button {
  min-height: 44px;
  padding: 0 20px;
  border: 0;
  border-radius: 10px;
  background: linear-gradient(135deg, #3867ff, #6845ef);
  color: white;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.control-row button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px 18px;
  border-radius: 12px;
}

.error-message {
  border: 1px solid #fecaca;
  background: #fff1f2;
  color: #b42318;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}

.summary-card,
.content-card {
  border: 1px solid #e0e6ef;
  background: white;
  box-shadow: 0 14px 38px rgb(31 50 81 / 7%);
}

.summary-card {
  padding: 22px;
  border-radius: 16px;
}

.summary-card span {
  display: block;
  margin-bottom: 10px;
  color: #7d879b;
  font-size: 13px;
}

.summary-card strong {
  font-size: 30px;
}

.content-card {
  padding: 26px;
  border-radius: 18px;
}

.challenge-history {
  margin-top: 18px;
}

.card-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 22px;
}

.card-heading h2 {
  margin: 0;
  font-size: 23px;
}

.card-heading select {
  min-width: 170px;
}

.empty-state {
  padding: 60px 20px;
  color: #7d879b;
  text-align: center;
}

.evidence-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.evidence-card {
  padding: 20px;
  border: 1px solid #e4e9f1;
  border-radius: 14px;
  background: #fcfdff;
}

.evidence-top,
.title-row,
.evidence-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.title-row {
  justify-content: flex-start;
}

.evidence-top h3 {
  margin: 0;
  font-size: 20px;
  text-transform: capitalize;
}

.evidence-top p {
  margin: 6px 0 0;
  color: #7d879b;
  font-size: 13px;
}

.strength-badge,
.difficulty-badge {
  padding: 5px 9px;
  border-radius: 99px;
  background: #edf2ff;
  color: #315ee8;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.strength-badge.strong {
  background: #dcfce7;
  color: #15803d;
}

.strength-badge.medium {
  background: #fff3cd;
  color: #9a6700;
}

.strength-badge.weak {
  background: #ffe4e6;
  color: #be123c;
}

.performance-score {
  text-align: right;
}

.performance-score span {
  display: block;
  color: #7d879b;
  font-size: 11px;
}

.performance-score strong {
  font-size: 28px;
}

.reason {
  min-height: 48px;
  margin: 18px 0;
  color: #56637a;
  line-height: 1.55;
}

.evidence-meta {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 9px;
}

.evidence-meta span {
  padding: 10px;
  border-radius: 9px;
  background: #f5f7fb;
  color: #8792a6;
  font-size: 11px;
}

.evidence-meta strong {
  display: block;
  margin-top: 5px;
  color: #24324b;
  font-size: 12px;
}

.evidence-footer {
  margin-top: 17px;
  padding-top: 14px;
  border-top: 1px solid #e8ecf3;
  color: #8792a6;
  font-size: 11px;
}

.evidence-footer code {
  color: #3867ff;
}

.record-count {
  color: #7d879b;
  font-size: 13px;
}

.history-table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th,
td {
  padding: 14px 12px;
  border-bottom: 1px solid #e7ebf2;
  text-align: left;
  white-space: nowrap;
}

th {
  color: #8792a6;
  font-size: 11px;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

td {
  color: #56637a;
  font-size: 13px;
}

td code {
  color: #3867ff;
}

@media (max-width: 1050px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .evidence-list {
    grid-template-columns: 1fr;
  }

  .evidence-meta {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .evidence-page {
    width: min(100% - 24px, 1460px);
  }

  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .user-controls {
    min-width: 0;
  }

  .control-row {
    flex-direction: column;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .card-heading {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>