<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";
import axios from "axios";

import {
  reportApi,
  type AssessmentReportResponse,
  type SkillState,
} from "../api/report";

const userId = ref(
  localStorage.getItem("skillmirror-user-id") || "U-WEB",
);

const report = ref<AssessmentReportResponse | null>(null);
const loading = ref(false);
const errorMessage = ref("");

const latest = computed(() => report.value?.latest ?? null);

const skills = computed<SkillState[]>(() => {
  return latest.value?.skill_mirror?.skills ?? [];
});

const latestScore = computed(() => {
  const value = latest.value?.score?.new_score;

  return typeof value === "number"
    ? value.toFixed(2)
    : "—";
});

const latestConfidence = computed(() => {
  const result = latest.value?.confidence;

  if (
    typeof result?.confidence_percent === "number"
  ) {
    return `${result.confidence_percent.toFixed(1)}%`;
  }

  if (typeof result?.confidence === "number") {
    return `${(result.confidence * 100).toFixed(1)}%`;
  }

  return "—";
});

const trustPassed = computed(() => {
  const trust = latest.value?.trust_summary;

  if (!trust) {
    return false;
  }

  return (
    trust.rejected_b_records_count === 0 &&
    trust.rejected_history_count === 0 &&
    trust.replayed_evidence_count === 0
  );
});

async function loadReport(): Promise<void> {
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

    report.value = await reportApi.getReport(
      cleanedUserId,
    );
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
        "Unable to load assessment report.";
    }
  } finally {
    loading.value = false;
  }
}

function skillName(skill: SkillState): string {
  return skill.skill_id || skill.id || "Unknown skill";
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
    : "—";
}

function scoreWidth(value: unknown): string {
  if (typeof value !== "number") {
    return "0%";
  }

  return `${Math.min(100, Math.max(0, value))}%`;
}

function confidenceText(value: unknown): string {
  if (typeof value !== "number") {
    return "—";
  }

  const percent = value <= 1 ? value * 100 : value;

  return `${percent.toFixed(0)}%`;
}

function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) {
    return "—";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

onMounted(() => {
  void loadReport();
});
</script>

<template>
  <main class="report-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">ASSESSMENT ANALYTICS</p>
        <h1>Skill Report</h1>
        <p class="subtitle">
          Scores and confidence are calculated from verified
          evidence across independent assessment sessions.
        </p>
      </div>

      <div class="user-controls">
        <label for="report-user-id">User ID</label>

        <div class="control-row">
          <input
            id="report-user-id"
            v-model="userId"
            type="text"
            :disabled="loading"
            @keyup.enter="loadReport"
          />

          <button
            type="button"
            :disabled="loading"
            @click="loadReport"
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
      <strong>Unable to load report</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <section
      v-if="loading && !report"
      class="empty-card"
    >
      Loading assessment report...
    </section>

    <section
      v-else-if="!latest"
      class="empty-card"
    >
      <div class="empty-icon">◎</div>
      <h2>No assessment report yet</h2>
      <p>
        Complete a challenge before viewing this report.
      </p>
    </section>

    <template v-else>
      <section class="summary-grid">
        <article class="summary-card score-card">
          <span>Latest Score</span>
          <strong>{{ latestScore }}</strong>

          <small>
            {{
              latest.score.score_status ||
              "Not classified"
            }}
          </small>
        </article>

        <article class="summary-card confidence-card">
          <span>Confidence</span>
          <strong>{{ latestConfidence }}</strong>

          <small>
            {{
              latest.confidence.confidence_status ||
              "Not classified"
            }}
          </small>
        </article>

        <article class="summary-card">
          <span>Completed Assessments</span>
          <strong>
            {{ report?.total_assessments ?? 0 }}
          </strong>

          <small>Independent sessions</small>
        </article>

        <article class="summary-card">
          <span>Accepted Evidence</span>
          <strong>
            {{ latest.evidence_summary.accepted_count }}
          </strong>

          <small>
            {{ latest.evidence_summary.rejected_count }}
            rejected
          </small>
        </article>
      </section>

      <section class="content-card">
        <div class="card-heading">
          <div>
            <p class="section-label">SKILL MIRROR</p>
            <h2>Measured Programming Skills</h2>
          </div>

          <span class="updated-time">
            Updated {{ formatDate(latest.created_at) }}
          </span>
        </div>

        <div
          v-if="!skills.length"
          class="empty-state"
        >
          No skill states were returned.
        </div>

        <div v-else class="skills-grid">
          <article
            v-for="skill in skills"
            :key="skillName(skill)"
            class="skill-card"
          >
            <div class="skill-heading">
              <div>
                <h3>
                  {{ displayName(skillName(skill)) }}
                </h3>

                <span>
                  {{ skill.evidence_count ?? 0 }}
                  evidence items
                </span>
              </div>

              <strong>
                {{ scoreText(skill.score) }}
              </strong>
            </div>

            <div class="progress-track">
              <div
                class="progress-value"
                :style="{
                  width: scoreWidth(skill.score),
                }"
              ></div>
            </div>

            <div class="skill-footer">
              <span>
                Confidence
                <strong>
                  {{ confidenceText(skill.confidence) }}
                </strong>
              </span>

              <span>
                Status
                <strong>
                  {{
                    typeof skill.score === "number"
                      ? skill.score >= 80
                        ? "Strong"
                        : skill.score >= 60
                          ? "Developing"
                          : "Needs evidence"
                      : "Unknown"
                  }}
                </strong>
              </span>
            </div>

            <div
              v-if="skill.subskills?.length"
              class="subskills"
            >
              <div
                v-for="(
                  subskill,
                  index
                ) in skill.subskills"
                :key="
                  subskill.id ||
                  subskill.sub_skill_id ||
                  index
                "
                class="subskill-row"
              >
                <span>
                  {{
                    displayName(
                      subskill.id ||
                      subskill.sub_skill_id,
                    )
                  }}
                </span>

                <strong>
                  {{ scoreText(subskill.score) }}
                </strong>
              </div>
            </div>
          </article>
        </div>
      </section>

      <section class="lower-grid">
        <article class="content-card next-card">
          <div class="card-heading">
            <div>
              <p class="section-label">NEXT CHALLENGE</p>
              <h2>Examiner Recommendation</h2>
            </div>

            <span class="difficulty-badge">
              {{
                latest.next_examiner.difficulty ||
                "Unknown"
              }}
            </span>
          </div>

          <div class="next-target">
            <span>Target skill</span>
            <strong>
              {{
                displayName(
                  latest.next_examiner.target_skill,
                )
              }}
            </strong>
          </div>

          <div class="next-target">
            <span>Target subskill</span>
            <strong>
              {{
                displayName(
                  latest.next_examiner.target_subskill,
                )
              }}
            </strong>
          </div>

          <p class="next-reason">
            {{
              latest.next_examiner.reason ||
              "No examiner explanation was returned."
            }}
          </p>

          <div class="next-meta">
            <span>
              Type:
              {{
                displayName(
                  latest.next_examiner.challenge_type,
                )
              }}
            </span>

            <span>
              Mode:
              {{
                displayName(
                  latest.next_examiner.mode,
                )
              }}
            </span>
          </div>
        </article>

        <article class="content-card trust-card">
          <div class="card-heading">
            <div>
              <p class="section-label">TRUST STATUS</p>
              <h2>Verification Summary</h2>
            </div>

            <span
              class="trust-badge"
              :class="{ passed: trustPassed }"
            >
              {{ trustPassed ? "VERIFIED" : "REVIEW" }}
            </span>
          </div>

          <div class="trust-list">
            <div>
              <span>Rejected B records</span>
              <strong>
                {{
                  latest.trust_summary
                    .rejected_b_records_count
                }}
              </strong>
            </div>

            <div>
              <span>Rejected history</span>
              <strong>
                {{
                  latest.trust_summary
                    .rejected_history_count
                }}
              </strong>
            </div>

            <div>
              <span>Replayed evidence</span>
              <strong>
                {{
                  latest.trust_summary
                    .replayed_evidence_count
                }}
              </strong>
            </div>
          </div>

          <p class="trust-note">
            Browser-supplied verification status is never
            trusted. Verification is determined by the A/B
            signed evidence pipeline.
          </p>
        </article>
      </section>

      <section class="content-card history-card">
        <div class="card-heading">
          <div>
            <p class="section-label">SCORE HISTORY</p>
            <h2>Assessment Timeline</h2>
          </div>

          <span class="updated-time">
            {{ report?.history.length ?? 0 }} records
          </span>
        </div>

        <div class="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Date</th>
                <th>Challenge</th>
                <th>Skill</th>
                <th>Difficulty</th>
                <th>Score</th>
                <th>Confidence</th>
                <th>Status</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="item in report?.history"
                :key="item.session_id"
              >
                <td>{{ formatDate(item.created_at) }}</td>
                <td>
                  <strong>{{ item.challenge_id }}</strong>
                </td>
                <td>
                  {{ displayName(item.target_skill) }}
                </td>
                <td>
                  <span class="difficulty-badge">
                    {{ item.difficulty || "—" }}
                  </span>
                </td>
                <td>{{ scoreText(item.score) }}</td>
                <td>
                  {{
                    confidenceText(
                      item.confidence_percent,
                    )
                  }}
                </td>
                <td>
                  {{ item.score_status || "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.report-page {
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
  max-width: 720px;
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

.control-row input {
  min-width: 190px;
  min-height: 44px;
  padding: 0 14px;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  background: white;
  outline: none;
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

.empty-card,
.content-card,
.summary-card {
  border: 1px solid #e0e6ef;
  background: white;
  box-shadow: 0 14px 38px rgb(31 50 81 / 7%);
}

.empty-card {
  padding: 80px 20px;
  border-radius: 18px;
  text-align: center;
}

.empty-icon {
  color: #3867ff;
  font-size: 48px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 18px;
}

.summary-card {
  padding: 22px;
  border-radius: 16px;
}

.summary-card > span {
  display: block;
  margin-bottom: 10px;
  color: #7d879b;
  font-size: 13px;
}

.summary-card > strong {
  display: block;
  font-size: 32px;
}

.summary-card small {
  color: #8792a6;
  text-transform: capitalize;
}

.score-card {
  border-left: 5px solid #3867ff;
}

.confidence-card {
  border-left: 5px solid #7c4dff;
}

.content-card {
  padding: 26px;
  border-radius: 18px;
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

.updated-time {
  color: #7d879b;
  font-size: 12px;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 14px;
}

.skill-card {
  padding: 20px;
  border: 1px solid #e4e9f1;
  border-radius: 14px;
  background: #fcfdff;
}

.skill-heading {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.skill-heading h3 {
  margin: 0;
  font-size: 19px;
}

.skill-heading span {
  color: #8490a5;
  font-size: 12px;
}

.skill-heading > strong {
  font-size: 29px;
}

.progress-track {
  height: 9px;
  margin: 17px 0;
  overflow: hidden;
  border-radius: 99px;
  background: #e9edf4;
}

.progress-value {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #3867ff, #7c4dff);
}

.skill-footer {
  display: flex;
  justify-content: space-between;
  color: #8490a5;
  font-size: 12px;
}

.skill-footer strong {
  margin-left: 6px;
  color: #24324b;
}

.subskills {
  display: grid;
  gap: 8px;
  margin-top: 17px;
  padding-top: 14px;
  border-top: 1px solid #e5e9f1;
}

.subskill-row {
  display: flex;
  justify-content: space-between;
  color: #667289;
  font-size: 12px;
}

.lower-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-top: 18px;
}

.difficulty-badge,
.trust-badge {
  padding: 6px 10px;
  border-radius: 99px;
  background: #fff3cd;
  color: #9a6700;
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
}

.trust-badge.passed {
  background: #dcfce7;
  color: #15803d;
}

.next-target {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  padding: 14px;
  border-radius: 10px;
  background: #f5f7fb;
}

.next-target span {
  color: #7d879b;
}

.next-reason {
  margin: 18px 0;
  color: #56637a;
  line-height: 1.6;
}

.next-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  color: #7d879b;
  font-size: 12px;
}

.trust-list {
  display: grid;
  gap: 10px;
}

.trust-list div {
  display: flex;
  justify-content: space-between;
  padding: 13px;
  border-radius: 9px;
  background: #f5f7fb;
}

.trust-note {
  margin: 16px 0 0;
  color: #7d879b;
  font-size: 12px;
  line-height: 1.6;
}

.history-card {
  margin-top: 18px;
}

.table-wrapper {
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

.empty-state {
  padding: 50px 20px;
  color: #7d879b;
  text-align: center;
}

@media (max-width: 1000px) {
  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .skills-grid,
  .lower-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .report-page {
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
}
</style>