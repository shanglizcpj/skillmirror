<script setup lang="ts">
import {
  computed,
  onMounted,
  ref,
} from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

import {
  reportApi,
  type AssessmentHistoryItem,
  type AssessmentReportResponse,
  type SkillState,
} from "../api/report";

const router = useRouter();

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

const measuredSkills = computed(() => {
  return skills.value.filter(
    (skill) => typeof skill.score === "number",
  );
});

const overallScore = computed(() => {
  const values = measuredSkills.value
    .map((skill) => skill.score)
    .filter(
      (value): value is number =>
        typeof value === "number",
    );

  if (!values.length) {
    return "—";
  }

  const average =
    values.reduce((total, value) => total + value, 0) /
    values.length;

  return average.toFixed(1);
});

const averageConfidence = computed(() => {
  const values = skills.value
    .map((skill) => skill.confidence)
    .filter(
      (value): value is number =>
        typeof value === "number",
    );

  if (!values.length) {
    return "—";
  }

  const average =
    values.reduce((total, value) => total + value, 0) /
    values.length;

  return `${(average * 100).toFixed(1)}%`;
});

const totalEvidence = computed(() => {
  return skills.value.reduce(
    (total, skill) =>
      total + (skill.evidence_count ?? 0),
    0,
  );
});

async function loadSkillMirror(): Promise<void> {
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
        "Unable to load Skill Mirror.";
    }
  } finally {
    loading.value = false;
  }
}

function skillId(skill: SkillState): string {
  return skill.skill_id || skill.id || "unknown";
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

function scoreWidth(value: unknown): string {
  if (typeof value !== "number") {
    return "0%";
  }

  return `${Math.min(100, Math.max(0, value))}%`;
}

function confidenceText(value: unknown): string {
  if (typeof value !== "number") {
    return "0%";
  }

  const percent = value <= 1 ? value * 100 : value;

  return `${percent.toFixed(0)}%`;
}

function skillStatus(value: unknown): string {
  if (typeof value !== "number") {
    return "Unknown";
  }

  if (value >= 80) {
    return "Strong";
  }

  if (value >= 60) {
    return "Developing";
  }

  return "Needs Attention";
}

function statusClass(value: unknown): string {
  if (typeof value !== "number") {
    return "unknown";
  }

  if (value >= 80) {
    return "strong";
  }

  if (value >= 60) {
    return "developing";
  }

  return "attention";
}

function historyForSkill(
  skill: SkillState,
): AssessmentHistoryItem[] {
  const id = skillId(skill);

  return (report.value?.history ?? []).filter(
    (item) => item.target_skill === id,
  );
}

function trendDelta(skill: SkillState): string {
  const history = historyForSkill(skill);

  if (history.length < 2) {
    return history.length === 1
      ? "First verified result"
      : "No verified trend yet";
  }

  const previous = history.at(-2)?.score;
  const current = history.at(-1)?.score;

  if (
    typeof previous !== "number" ||
    typeof current !== "number"
  ) {
    return "Trend unavailable";
  }

  const delta = current - previous;

  if (Math.abs(delta) < 0.01) {
    return "No score change";
  }

  return `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`;
}

function trendClass(skill: SkillState): string {
  const history = historyForSkill(skill);

  if (history.length < 2) {
    return "neutral";
  }

  const previous = history.at(-2)?.score;
  const current = history.at(-1)?.score;

  if (
    typeof previous !== "number" ||
    typeof current !== "number"
  ) {
    return "neutral";
  }

  if (current > previous) {
    return "positive";
  }

  if (current < previous) {
    return "negative";
  }

  return "neutral";
}

function sparklinePoints(skill: SkillState): string {
  const history = historyForSkill(skill);

  const values = history
    .map((item) => item.score)
    .filter(
      (value): value is number =>
        typeof value === "number",
    );

  if (!values.length) {
    const current = skill.score;

    if (typeof current !== "number") {
      return "";
    }

    const y = 55 - current * 0.5;
    return `0,${y} 100,${y}`;
  }

  if (values.length === 1) {
    const y = 55 - values[0] * 0.5;
    return `0,${y} 100,${y}`;
  }

  return values
    .map((value, index) => {
      const x =
        (index / (values.length - 1)) * 100;

      const y = 55 - value * 0.5;

      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
}

function accentClass(index: number): string {
  const accents = [
    "blue",
    "purple",
    "teal",
    "orange",
    "pink",
  ];

  return accents[index % accents.length];
}

function goToChallenge(): void {
  void router.push("/challenge");
}

onMounted(() => {
  void loadSkillMirror();
});
</script>

<template>
  <main class="mirror-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">PROGRAMMING DIGITAL TWIN</p>
        <h1>Skill Mirror</h1>

        <p class="subtitle">
          Every score is supported by verified behavior,
          trusted evidence, and confidence-aware assessment.
        </p>
      </div>

      <div class="page-actions">
        <div class="user-control">
          <label for="mirror-user-id">User ID</label>

          <input
            id="mirror-user-id"
            v-model="userId"
            type="text"
            :disabled="loading"
            @keyup.enter="loadSkillMirror"
          />
        </div>

        <button
          class="refresh-button"
          type="button"
          :disabled="loading"
          @click="loadSkillMirror"
        >
          {{ loading ? "Loading..." : "Refresh" }}
        </button>

        <button
          class="challenge-button"
          type="button"
          @click="goToChallenge"
        >
          Continue Assessment
        </button>
      </div>
    </section>

    <div
      v-if="errorMessage"
      class="message error-message"
    >
      <strong>Unable to load Skill Mirror</strong>
      <span>{{ errorMessage }}</span>
    </div>

    <section
      v-if="loading && !report"
      class="empty-card"
    >
      Loading Skill Mirror...
    </section>

    <section
      v-else-if="!latest"
      class="empty-card"
    >
      <div class="empty-icon">S</div>
      <h2>No verified Skill Mirror yet</h2>
      <p>
        Complete your first challenge to create a
        confidence-aware skill profile.
      </p>

      <button
        class="challenge-button"
        type="button"
        @click="goToChallenge"
      >
        Start Assessment
      </button>
    </section>

    <template v-else>
      <section class="summary-grid">
        <article class="summary-card">
          <span>Overall Score</span>
          <strong>{{ overallScore }}</strong>
          <small>
            {{ measuredSkills.length }} measured skills
          </small>
        </article>

        <article class="summary-card">
          <span>Average Confidence</span>
          <strong>{{ averageConfidence }}</strong>
          <small>
            Confidence is independent from score
          </small>
        </article>

        <article class="summary-card">
          <span>Evidence Collected</span>
          <strong>{{ totalEvidence }}</strong>
          <small>Verified evidence records</small>
        </article>

        <article class="summary-card">
          <span>Assessment Sessions</span>
          <strong>
            {{ report?.total_assessments ?? 0 }}
          </strong>
          <small>Completed challenge sessions</small>
        </article>
      </section>

      <section class="skills-heading">
        <div>
          <p class="section-label">ABILITY PROFILE</p>
          <h2>Measured Skills</h2>
        </div>

        <span>
          Latest challenge:
          <strong>{{ latest.challenge_id }}</strong>
        </span>
      </section>

      <section class="skills-grid">
        <article
          v-for="(skill, index) in skills"
          :key="skillId(skill)"
          class="skill-card"
          :class="accentClass(index)"
        >
          <div class="skill-top">
            <div>
              <h3>
                {{ displayName(skillId(skill)) }}
              </h3>

              <span
                class="status-badge"
                :class="statusClass(skill.score)"
              >
                {{ skillStatus(skill.score) }}
              </span>
            </div>

            <strong class="skill-score">
              {{ scoreText(skill.score) }}
            </strong>
          </div>

          <div class="score-progress">
            <div
              class="score-progress-value"
              :style="{
                width: scoreWidth(skill.score),
              }"
            ></div>
          </div>

          <div class="skill-metrics">
            <div>
              <span>Confidence</span>
              <strong>
                {{ confidenceText(skill.confidence) }}
              </strong>
            </div>

            <div>
              <span>Evidence</span>
              <strong>
                {{ skill.evidence_count ?? 0 }}
              </strong>
            </div>

            <div>
              <span>Trend</span>
              <strong :class="trendClass(skill)">
                {{ trendDelta(skill) }}
              </strong>
            </div>
          </div>

          <div class="trend-chart">
            <div class="trend-label">
              <span>Verified score trend</span>
              <span>
                {{ historyForSkill(skill).length }}
                points
              </span>
            </div>

            <svg
              viewBox="0 0 100 60"
              preserveAspectRatio="none"
              aria-label="Skill score trend"
            >
              <line
                x1="0"
                y1="55"
                x2="100"
                y2="55"
                class="axis-line"
              />

              <line
                x1="0"
                y1="30"
                x2="100"
                y2="30"
                class="grid-line"
              />

              <polyline
                v-if="sparklinePoints(skill)"
                :points="sparklinePoints(skill)"
                class="trend-line"
                fill="none"
              />
            </svg>
          </div>

          <div
            v-if="skill.subskills?.length"
            class="subskill-list"
          >
            <div
              v-for="(
                subskill,
                subskillIndex
              ) in skill.subskills"
              :key="
                subskill.id ||
                subskill.sub_skill_id ||
                subskillIndex
              "
              class="subskill-item"
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
      </section>

      <section class="next-panel">
        <div>
          <p class="section-label">
            NEXT VERIFICATION TARGET
          </p>

          <h2>
            {{
              displayName(
                latest.next_examiner.target_skill,
              )
            }}
          </h2>

          <p>
            {{
              latest.next_examiner.reason ||
              "Continue collecting verified evidence."
            }}
          </p>
        </div>

        <div class="next-details">
          <span>
            Subskill
            <strong>
              {{
                displayName(
                  latest.next_examiner
                    .target_subskill,
                )
              }}
            </strong>
          </span>

          <span>
            Difficulty
            <strong>
              {{
                displayName(
                  latest.next_examiner.difficulty,
                )
              }}
            </strong>
          </span>

          <button
            class="challenge-button"
            type="button"
            @click="goToChallenge"
          >
            Start Next Challenge
          </button>
        </div>
      </section>
    </template>
  </main>
</template>

<style scoped>
.mirror-page {
  width: min(1460px, calc(100% - 48px));
  margin: 0 auto;
  padding: 42px 0 72px;
  color: #14213d;
}

.page-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 30px;
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

.page-actions {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}

.user-control label {
  display: block;
  margin-bottom: 6px;
  color: #758098;
  font-size: 12px;
  font-weight: 700;
}

.user-control input {
  width: 145px;
  min-height: 44px;
  padding: 0 13px;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  background: white;
  outline: none;
}

.refresh-button,
.challenge-button {
  min-height: 44px;
  padding: 0 18px;
  border-radius: 10px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
}

.refresh-button {
  border: 1px solid #d8dfeb;
  background: white;
  color: #26344d;
}

.challenge-button {
  border: 0;
  background: linear-gradient(
    135deg,
    #3867ff,
    #6845ef
  );
  color: white;
}

.refresh-button:disabled {
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
.summary-card,
.skill-card,
.next-panel {
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
  width: 60px;
  height: 60px;
  margin: 0 auto 17px;
  border-radius: 18px;
  background: linear-gradient(
    135deg,
    #3867ff,
    #6845ef
  );
  color: white;
  font-size: 34px;
  font-weight: 800;
  line-height: 60px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
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
  color: #8a95a9;
}

.skills-heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 16px;
}

.skills-heading h2 {
  margin: 0;
  font-size: 25px;
}

.skills-heading > span {
  color: #7d879b;
  font-size: 13px;
}

.skills-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.skill-card {
  --accent: #3867ff;
  padding: 22px;
  border-left: 5px solid var(--accent);
  border-radius: 16px;
}

.skill-card.purple {
  --accent: #7c4dff;
}

.skill-card.teal {
  --accent: #20b9a4;
}

.skill-card.orange {
  --accent: #f59e0b;
}

.skill-card.pink {
  --accent: #ec4899;
}

.skill-top,
.skill-top > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.skill-top h3 {
  margin: 0;
  font-size: 21px;
}

.skill-score {
  font-size: 34px;
}

.status-badge {
  padding: 5px 9px;
  border-radius: 99px;
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
}

.status-badge.strong {
  background: #dcfce7;
  color: #15803d;
}

.status-badge.developing {
  background: #eaf1ff;
  color: #315ee8;
}

.status-badge.attention {
  background: #fff3cd;
  color: #9a6700;
}

.status-badge.unknown {
  background: #eef1f5;
  color: #667085;
}

.score-progress {
  height: 9px;
  margin: 17px 0;
  overflow: hidden;
  border-radius: 99px;
  background: #e9edf4;
}

.score-progress-value {
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
}

.skill-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 9px;
}

.skill-metrics div {
  padding: 11px;
  border-radius: 9px;
  background: #f6f8fc;
}

.skill-metrics span {
  display: block;
  margin-bottom: 5px;
  color: #8792a6;
  font-size: 11px;
}

.skill-metrics strong {
  font-size: 13px;
}

.positive {
  color: #16845f;
}

.negative {
  color: #c2414b;
}

.neutral {
  color: #667085;
}

.trend-chart {
  margin-top: 17px;
  padding: 13px;
  border-radius: 10px;
  background: #f8faff;
}

.trend-label {
  display: flex;
  justify-content: space-between;
  color: #8490a5;
  font-size: 10px;
}

.trend-chart svg {
  width: 100%;
  height: 72px;
  overflow: visible;
}

.axis-line,
.grid-line {
  stroke: #e0e6ef;
  stroke-width: 1;
}

.grid-line {
  stroke-dasharray: 3 3;
}

.trend-line {
  stroke: var(--accent);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
  vector-effect: non-scaling-stroke;
}

.subskill-list {
  display: grid;
  gap: 7px;
  margin-top: 14px;
}

.subskill-item {
  display: flex;
  justify-content: space-between;
  padding: 9px 11px;
  border-radius: 8px;
  background: #f6f8fc;
  color: #667289;
  font-size: 12px;
}

.next-panel {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 30px;
  margin-top: 18px;
  padding: 26px;
  border-radius: 18px;
}

.next-panel h2 {
  margin: 0;
  font-size: 26px;
}

.next-panel p {
  max-width: 760px;
  margin: 9px 0 0;
  color: #667289;
  line-height: 1.6;
}

.next-details {
  display: flex;
  align-items: center;
  gap: 18px;
}

.next-details > span {
  color: #8792a6;
  font-size: 11px;
}

.next-details strong {
  display: block;
  margin-top: 5px;
  color: #24324b;
  font-size: 13px;
}

@media (max-width: 1050px) {
  .page-heading,
  .next-panel {
    align-items: stretch;
    flex-direction: column;
  }

  .page-actions,
  .next-details {
    flex-wrap: wrap;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 760px) {
  .mirror-page {
    width: min(100% - 24px, 1460px);
  }

  .page-actions,
  .next-details {
    align-items: stretch;
    flex-direction: column;
  }

  .user-control input {
    width: 100%;
  }

  .summary-grid,
  .skills-grid {
    grid-template-columns: 1fr;
  }

  .skills-heading {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }
}
</style>