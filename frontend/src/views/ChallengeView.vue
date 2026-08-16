<script setup lang="ts">
import { computed, ref, watch } from "vue";

import DemoUserSwitcher from "../components/DemoUserSwitcher.vue";
import MonacoCodeEditor from "../components/MonacoCodeEditor.vue";
import { useChallengeStore } from "../stores/challenge";


const store = useChallengeStore();
const userInput = ref(store.userId);


watch(
  () => store.userId,
  (newUserId) => {
    userInput.value = newUserId;
  },
);


const busyText = computed(() => {
  const texts = {
    starting: "Starting...",
    running: "Running...",
    hinting: "Loading Hint...",
    submitting: "Submitting...",
  };

  return store.busyAction
    ? texts[store.busyAction as keyof typeof texts]
    : "";
});


async function handleStart(): Promise<void> {
  store.setUserId(userInput.value);
  userInput.value = store.userId;

  await store.startChallenge();
}


async function handleRun(): Promise<void> {
  await store.runTests();
}


async function handleHint(): Promise<void> {
  await store.requestHint();
}


async function handleSubmit(): Promise<void> {
  await store.submitAssessment();
}


function formatValue(value: unknown): string {
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
</script>


<template>
  <main class="challenge-page">
    <section class="page-heading">
      <div>
        <p class="eyebrow">
          EVIDENCE-DRIVEN ASSESSMENT
        </p>

        <h1>Challenge Workspace</h1>

        <p class="subtitle">
          Repair the code, run trusted tests, request progressive hints,
          and submit verified evidence.
        </p>
      </div>

      <div class="start-panel">
        <label for="user-id">
          User ID
        </label>

        <div class="start-controls">
          <input
            id="user-id"
            v-model="userInput"
            type="text"
            :disabled="store.isBusy"
            placeholder="U-WEB"
          />

          <button
            class="button primary-button"
            type="button"
            :disabled="store.isBusy || !userInput.trim()"
            @click="handleStart"
          >
            {{
              store.busyAction === "starting"
                ? "Starting..."
                : store.challenge
                  ? "New Challenge"
                  : "Start Challenge"
            }}
          </button>
        </div>
      </div>
    </section>

    <DemoUserSwitcher />

    <div
      v-if="store.errorMessage"
      class="message error-message"
    >
      <strong>Request failed</strong>
      <span>{{ store.errorMessage }}</span>
    </div>

    <div
      v-if="busyText"
      class="message loading-message"
    >
      {{ busyText }}
    </div>

    <section
      v-if="!store.challenge"
      class="empty-card"
    >
      <div class="empty-icon">
        &lt;/&gt;
      </div>

      <h2>No active challenge</h2>

      <p>
        Click “Start Challenge” to request a Challenge from A.
      </p>
    </section>

    <template v-else>
      <section class="session-strip">
        <span>
          Session
          <strong>{{ store.sessionId }}</strong>
        </span>

        <span>
          Challenge
          <strong>
            {{ store.challenge.challenge_id }}
          </strong>
        </span>

        <span>
          Skill
          <strong>
            {{ store.challenge.target_skill || "Unknown" }}
          </strong>
        </span>

        <span>
          Difficulty
          <strong>
            {{ store.challenge.difficulty || "Unknown" }}
          </strong>
        </span>
      </section>

      <section class="workspace-grid">
        <article class="panel problem-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-label">
                PROBLEM
              </p>

              <h2>
                {{
                  store.challenge.title ||
                  "Programming Challenge"
                }}
              </h2>
            </div>

            <span class="challenge-badge">
              {{ store.challenge.challenge_id }}
            </span>
          </div>

          <p class="task-description">
            {{
              store.challenge.task_description ||
              "Complete the function and pass all trusted tests."
            }}
          </p>

          <div class="detail-grid">
            <div class="detail-item">
              <span>Entry point</span>

              <code>
                {{ store.challenge.entry_point || "Unknown" }}
              </code>
            </div>

            <div class="detail-item">
              <span>Target subskill</span>

              <strong>
                {{
                  store.challenge.target_subskill ||
                  "Unknown"
                }}
              </strong>
            </div>
          </div>

          <div class="public-tests">
            <div class="section-title">
              <h3>Public Tests</h3>

              <span>
                {{
                  store.challenge.public_tests?.length ||
                  0
                }}
                visible
              </span>
            </div>

            <div
              v-if="store.challenge.public_tests?.length"
              class="test-list"
            >
              <div
                v-for="test in store.challenge.public_tests"
                :key="test.case_id"
                class="public-test"
              >
                <div class="test-name">
                  <span class="test-dot"></span>
                  {{ test.case_id }}
                </div>

                <div class="test-values">
                  <span>
                    Input:
                    <code>
                      {{ formatValue(test.args) }}
                    </code>
                  </span>

                  <span v-if="'expected' in test">
                    Expected:
                    <code>
                      {{ formatValue(test.expected) }}
                    </code>
                  </span>

                  <span v-else>
                    Expected exception:
                    <code>
                      {{ test.expected_exception }}
                    </code>
                  </span>
                </div>
              </div>
            </div>

            <p
              v-else
              class="muted-text"
            >
              Public test details are not available.
            </p>
          </div>

          <div class="security-note">
            <strong>
              Hidden tests protected
            </strong>

            <p>
              Hidden test cases and reference solutions remain in the
              B backend and are never sent to this browser.
            </p>
          </div>
        </article>

        <article class="panel editor-panel">
          <div class="panel-heading">
            <div>
              <p class="panel-label">
                PYTHON EDITOR
              </p>

              <h2>Solution</h2>
            </div>

            <span class="language-badge">
              Python 3.12
            </span>
          </div>

          <div class="editor-shell">
            <MonacoCodeEditor
              v-model="store.code"
              height="480px"
            />
          </div>

          <div class="action-row">
            <button
              class="button secondary-button"
              type="button"
              :disabled="
                store.isBusy ||
                !store.hasActiveChallenge
              "
              @click="handleRun"
            >
              {{
                store.busyAction === "running"
                  ? "Running..."
                  : "Run Tests"
              }}
            </button>

            <button
              class="button hint-button"
              type="button"
              :disabled="
                store.isBusy ||
                !store.hasActiveChallenge
              "
              @click="handleHint"
            >
              {{
                store.busyAction === "hinting"
                  ? "Loading..."
                  : "Get Hint"
              }}
            </button>

            <button
              class="button submit-button"
              type="button"
              :disabled="
                store.isBusy ||
                !store.hasActiveChallenge
              "
              @click="handleSubmit"
            >
              {{
                store.busyAction === "submitting"
                  ? "Submitting..."
                  : "Submit Assessment"
              }}
            </button>
          </div>
        </article>
      </section>

      <section class="results-grid">
        <article class="panel result-panel">
          <div class="section-title">
            <h3>Test Results</h3>

            <span
              v-if="store.testResult"
              class="result-status"
              :class="{
                passed: store.allTestsPassed,
                failed: !store.allTestsPassed,
              }"
            >
              {{
                store.allTestsPassed
                  ? "PASSED"
                  : "FAILED"
              }}
            </span>
          </div>

          <div
            v-if="store.testResult"
            class="result-content"
          >
            <div class="score-line">
              <strong>
                {{ store.testResult.passed }}/{{
                  store.testResult.total
                }}
              </strong>

              <span>tests passed</span>
            </div>

            <div class="progress-track">
              <div
                class="progress-value"
                :class="{
                  complete: store.allTestsPassed,
                }"
                :style="{
                  width:
                    store.testResult.total > 0
                      ? `${(
                          store.testResult.passed /
                          store.testResult.total
                        ) * 100}%`
                      : '0%',
                }"
              ></div>
            </div>

            <div class="result-details">
              <span>
                Public:
                {{ store.testResult.public_passed }}/{{
                  store.testResult.public_total
                }}
              </span>

              <span>
                Hidden:
                {{ store.testResult.hidden_passed }}/{{
                  store.testResult.hidden_total
                }}
              </span>

              <span>
                Runtime:
                {{
                  store.testResult.runtime.toFixed(3)
                }}s
              </span>

              <span>
                Sandbox:
                {{ store.testResult.sandbox_mode }}
              </span>
            </div>

            <div
              v-if="store.testResult.failed_cases.length"
              class="failed-list"
            >
              <h4>Failed cases</h4>

              <div
                v-for="(
                  failedCase,
                  index
                ) in store.testResult.failed_cases"
                :key="index"
                class="failed-case"
              >
                {{
                  failedCase.message ||
                  `Test ${index + 1} failed`
                }}
              </div>
            </div>
          </div>

          <p
            v-else
            class="muted-text"
          >
            Run the code to create a signed test result.
          </p>
        </article>

        <article class="panel hint-panel">
          <div class="section-title">
            <h3>Progressive Hint</h3>

            <span
              v-if="store.hintResult?.hint_level"
              class="hint-level"
            >
              Level {{ store.hintResult.hint_level }}
            </span>
          </div>

          <div
            v-if="store.hintResult"
            class="hint-content"
          >
            <strong>
              {{ store.hintResult.action }}
            </strong>

            <p>
              {{
                store.hintResult.message ||
                store.hintResult.reason ||
                "No hint is available."
              }}
            </p>

            <small v-if="store.hintResult.source">
              Source:
              {{ store.hintResult.source }}
            </small>
          </div>

          <p
            v-else
            class="muted-text"
          >
            Run the starter code, then request a progressive hint.
          </p>
        </article>
      </section>

      <section
        v-if="store.assessmentResult"
        class="panel assessment-panel"
      >
        <div class="assessment-heading">
          <div>
            <p class="panel-label">
              ASSESSMENT COMPLETE
            </p>

            <h2>Verified Skill Update</h2>
          </div>

          <span class="completed-badge">
            COMPLETED
          </span>
        </div>

        <div class="assessment-metrics">
          <div class="metric-card">
            <span>Score</span>

            <strong>
              {{
                store.assessmentResult.score
                  ?.new_score !== undefined
                  ? store.assessmentResult.score
                      .new_score.toFixed(2)
                  : "--"
              }}
            </strong>
          </div>

          <div class="metric-card">
            <span>Confidence</span>

            <strong>
              {{
                store.assessmentResult.confidence
                  ?.confidence_percent !== undefined
                  ? `${store.assessmentResult.confidence
                      .confidence_percent.toFixed(1)}%`
                  : store.assessmentResult.confidence
                        ?.confidence !== undefined
                    ? `${(
                        store.assessmentResult.confidence
                          .confidence * 100
                      ).toFixed(1)}%`
                    : "--"
              }}
            </strong>
          </div>

          <div class="metric-card">
            <span>Challenge</span>

            <strong>
              {{ store.challenge.challenge_id }}
            </strong>
          </div>
        </div>

        <details class="json-details">
          <summary>
            View updated Skill Mirror
          </summary>

          <pre>{{
            JSON.stringify(
              store.assessmentResult.updated_skill_mirror,
              null,
              2,
            )
          }}</pre>
        </details>

        <details class="json-details">
          <summary>
            View trust report
          </summary>

          <pre>{{
            JSON.stringify(
              store.assessmentResult.trust_report,
              null,
              2,
            )
          }}</pre>
        </details>
      </section>
    </template>
  </main>
</template>


<style scoped>
.challenge-page {
  width: min(1500px, calc(100% - 48px));
  margin: 0 auto;
  padding: 40px 0 72px;
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
.panel-label {
  margin: 0 0 8px;
  color: #3867ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.page-heading h1 {
  margin: 0;
  font-size: clamp(32px, 4vw, 52px);
  line-height: 1.05;
}

.subtitle {
  max-width: 720px;
  margin: 12px 0 0;
  color: #6d7890;
  font-size: 16px;
}

.start-panel {
  min-width: 360px;
}

.start-panel label {
  display: block;
  margin-bottom: 7px;
  color: #758098;
  font-size: 13px;
  font-weight: 700;
}

.start-controls {
  display: flex;
  gap: 10px;
}

.start-controls input {
  min-width: 150px;
  padding: 0 14px;
  border: 1px solid #d8dfeb;
  border-radius: 10px;
  background: #fff;
  color: #14213d;
  outline: none;
}

.start-controls input:focus {
  border-color: #3867ff;
  box-shadow: 0 0 0 3px rgb(56 103 255 / 12%);
}

.button {
  min-height: 44px;
  padding: 0 18px;
  border: 0;
  border-radius: 10px;
  font: inherit;
  font-weight: 750;
  cursor: pointer;
  transition:
    transform 0.16s ease,
    opacity 0.16s ease;
}

.button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.primary-button,
.submit-button {
  background: linear-gradient(
    135deg,
    #3867ff,
    #6845ef
  );
  color: white;
}

.secondary-button {
  background: #eaf1ff;
  color: #2456df;
}

.hint-button {
  background: #fff5d9;
  color: #9a6700;
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

.loading-message {
  border: 1px solid #bfdbfe;
  background: #eff6ff;
  color: #2456df;
}

.empty-card,
.panel,
.session-strip {
  border: 1px solid #e0e6ef;
  background: #fff;
  box-shadow: 0 14px 38px rgb(31 50 81 / 7%);
}

.empty-card {
  padding: 90px 24px;
  border-radius: 18px;
  text-align: center;
}

.empty-icon {
  margin-bottom: 18px;
  color: #3867ff;
  font-family: monospace;
  font-size: 48px;
  font-weight: 800;
}

.empty-card h2 {
  margin: 0 0 10px;
}

.empty-card p,
.muted-text {
  color: #7d879b;
}

.session-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 26px;
  margin-bottom: 18px;
  padding: 15px 20px;
  border-radius: 14px;
}

.session-strip span {
  color: #7d879b;
  font-size: 13px;
}

.session-strip strong {
  margin-left: 7px;
  color: #14213d;
}

.workspace-grid,
.results-grid {
  display: grid;
  grid-template-columns:
    minmax(330px, 0.8fr)
    minmax(520px, 1.35fr);
  gap: 18px;
}

.results-grid {
  grid-template-columns: 1.2fr 0.8fr;
  margin-top: 18px;
}

.panel {
  padding: 24px;
  border-radius: 18px;
}

.panel-heading,
.section-title,
.assessment-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.panel-heading h2,
.assessment-heading h2 {
  margin: 0;
  font-size: 23px;
}

.challenge-badge,
.language-badge,
.hint-level,
.completed-badge,
.result-status {
  padding: 7px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 800;
}

.challenge-badge,
.language-badge {
  background: #edf2ff;
  color: #315ee8;
}

.task-description {
  margin: 24px 0;
  color: #46536a;
  font-size: 15px;
  line-height: 1.75;
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 26px;
}

.detail-item {
  padding: 14px;
  border-radius: 12px;
  background: #f7f9fc;
}

.detail-item span {
  display: block;
  margin-bottom: 7px;
  color: #8490a5;
  font-size: 12px;
}

.detail-item code {
  color: #7646e8;
  font-weight: 750;
}

.section-title {
  align-items: center;
  margin-bottom: 14px;
}

.section-title h3 {
  margin: 0;
  font-size: 17px;
}

.section-title > span {
  color: #7d879b;
  font-size: 12px;
}

.test-list {
  display: grid;
  gap: 10px;
}

.public-test {
  padding: 13px;
  border: 1px solid #e7ebf2;
  border-radius: 12px;
}

.test-name {
  display: flex;
  align-items: center;
  margin-bottom: 9px;
  font-weight: 750;
}

.test-dot {
  width: 8px;
  height: 8px;
  margin-right: 8px;
  border-radius: 50%;
  background: #31b98b;
}

.test-values {
  display: grid;
  gap: 5px;
  color: #6f7b90;
  font-size: 12px;
}

.test-values code {
  color: #26344d;
}

.security-note {
  margin-top: 20px;
  padding: 15px;
  border-left: 4px solid #31b98b;
  border-radius: 8px;
  background: #effcf7;
  color: #18775a;
}

.security-note p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.5;
}

.editor-shell {
  height: 480px;
  margin-top: 18px;
  overflow: hidden;
  border: 1px solid #273246;
  border-radius: 12px;
  background: #111827;
}

.editor-shell :deep(*) {
  max-width: 100%;
}

.action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.submit-button {
  margin-left: auto;
}

.score-line {
  display: flex;
  align-items: baseline;
  gap: 9px;
}

.score-line strong {
  font-size: 34px;
}

.score-line span {
  color: #7d879b;
}

.progress-track {
  height: 9px;
  margin: 15px 0;
  overflow: hidden;
  border-radius: 99px;
  background: #e9edf4;
}

.progress-value {
  height: 100%;
  border-radius: inherit;
  background: #f59e0b;
  transition: width 0.3s ease;
}

.progress-value.complete {
  background: #20b486;
}

.result-details {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: #667289;
  font-size: 12px;
}

.result-status.passed {
  background: #dcfce7;
  color: #15803d;
}

.result-status.failed {
  background: #fff0db;
  color: #b45309;
}

.failed-list {
  margin-top: 16px;
}

.failed-list h4 {
  margin: 0 0 8px;
}

.failed-case {
  margin-top: 7px;
  padding: 10px;
  border-radius: 8px;
  background: #fff1f2;
  color: #b42318;
  font-size: 13px;
}

.hint-level {
  background: #fff3cd;
  color: #9a6700;
}

.hint-content {
  padding: 16px;
  border-radius: 12px;
  background: #fffaf0;
  color: #7c5700;
}

.hint-content p {
  margin: 10px 0;
  line-height: 1.65;
}

.hint-content small {
  color: #98815b;
}

.assessment-panel {
  margin-top: 18px;
}

.completed-badge {
  background: #dcfce7;
  color: #15803d;
}

.assessment-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin: 22px 0;
}

.metric-card {
  padding: 18px;
  border-radius: 13px;
  background: #f6f8fc;
}

.metric-card span {
  display: block;
  margin-bottom: 8px;
  color: #7d879b;
  font-size: 12px;
}

.metric-card strong {
  font-size: 27px;
}

.json-details {
  margin-top: 12px;
  border: 1px solid #e2e7ef;
  border-radius: 10px;
}

.json-details summary {
  padding: 13px 15px;
  cursor: pointer;
  font-weight: 700;
}

.json-details pre {
  max-height: 320px;
  margin: 0;
  padding: 15px;
  overflow: auto;
  background: #111827;
  color: #d7e3f7;
  font-size: 12px;
}

@media (max-width: 1000px) {
  .page-heading {
    align-items: stretch;
    flex-direction: column;
  }

  .start-panel {
    min-width: 0;
  }

  .workspace-grid,
  .results-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 650px) {
  .challenge-page {
    width: min(100% - 24px, 1500px);
    padding-top: 24px;
  }

  .start-controls,
  .action-row {
    flex-direction: column;
  }

  .start-controls input {
    min-height: 44px;
  }

  .submit-button {
    margin-left: 0;
  }

  .detail-grid,
  .assessment-metrics {
    grid-template-columns: 1fr;
  }
}
</style>