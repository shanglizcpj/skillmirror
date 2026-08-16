import { computed, ref } from "vue";
import { defineStore } from "pinia";

import {
  challengeApi,
  getApiErrorMessage,
  type CompleteAssessmentResponse,
  type HintResponse,
  type LearnerChallenge,
  type RunTestsResponse,
} from "../api/challenge";

type BusyAction = "" | "starting" | "running" | "hinting" | "submitting";

export const useChallengeStore = defineStore("challenge", () => {
  const userId = ref(localStorage.getItem("skillmirror-user-id") || "U-WEB");

  const sessionId = ref("");
  const challenge = ref<LearnerChallenge | null>(null);
  const code = ref("");

  const testResult = ref<RunTestsResponse | null>(null);
  const hintResult = ref<HintResponse | null>(null);
  const assessmentResult = ref<CompleteAssessmentResponse | null>(null);

  const failedAttempts = ref(0);
  const startedAt = ref<number | null>(null);

  const busyAction = ref<BusyAction>("");
  const errorMessage = ref("");

  const isBusy = computed(() => busyAction.value !== "");

  const hasActiveChallenge = computed(() => {
    return (
      sessionId.value.length > 0 &&
      challenge.value !== null &&
      assessmentResult.value === null
    );
  });

  const allTestsPassed = computed(() => {
    const result = testResult.value;

    return (
      result !== null &&
      result.total > 0 &&
      result.passed === result.total
    );
  });

  function createSessionId(): string {
    const time = new Date()
      .toISOString()
      .replace(/[-:.TZ]/g, "")
      .slice(0, 14);

    const random = Math.random()
      .toString(36)
      .slice(2, 8)
      .toUpperCase();

    return `S-WEB-${time}-${random}`;
  }

  function setUserId(value: string): void {
    const cleaned = value.trim();

    if (!cleaned) {
      return;
    }

    userId.value = cleaned;
    localStorage.setItem("skillmirror-user-id", cleaned);
  }

  function clearResults(): void {
    testResult.value = null;
    hintResult.value = null;
    assessmentResult.value = null;
    failedAttempts.value = 0;
    errorMessage.value = "";
  }

  async function startChallenge(): Promise<boolean> {
    if (isBusy.value) {
      return false;
    }

    busyAction.value = "starting";
    errorMessage.value = "";

    try {
      const newSessionId = createSessionId();

      const response = await challengeApi.start({
        user_id: userId.value,
        session_id: newSessionId,
      });

      const learnerChallenge =
        response.challenge ?? response.learner_challenge;

      if (!learnerChallenge) {
        throw new Error("B 后端响应中没有 challenge 字段");
      }

      sessionId.value = response.session_id || newSessionId;
      challenge.value = learnerChallenge;
      code.value = learnerChallenge.starter_code || "";

      clearResults();
      startedAt.value = Date.now();

      return true;
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error);
      return false;
    } finally {
      busyAction.value = "";
    }
  }

  async function runTests(): Promise<RunTestsResponse | null> {
    if (!hasActiveChallenge.value) {
      errorMessage.value = "请先点击 Start Challenge";
      return null;
    }

    if (!code.value.trim()) {
      errorMessage.value = "代码不能为空";
      return null;
    }

    busyAction.value = "running";
    errorMessage.value = "";

    try {
      const result = await challengeApi.runTests({
        user_id: userId.value,
        session_id: sessionId.value,
        code: code.value,
        timeout_seconds: 3,
      });

      testResult.value = result;

      if (result.passed < result.total) {
        failedAttempts.value += 1;
      }

      return result;
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error);
      return null;
    } finally {
      busyAction.value = "";
    }
  }

  async function requestHint(): Promise<HintResponse | null> {
    if (!hasActiveChallenge.value) {
      errorMessage.value = "请先点击 Start Challenge";
      return null;
    }

    busyAction.value = "hinting";
    errorMessage.value = "";

    try {
      const result = await challengeApi.requestHint({
        user_id: userId.value,
        session_id: sessionId.value,
        user_code: code.value,
        failed_attempts: failedAttempts.value,
        asked_for_hint: true,
      });

      hintResult.value = result;
      return result;
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error);
      return null;
    } finally {
      busyAction.value = "";
    }
  }

  async function submitAssessment(): Promise<CompleteAssessmentResponse | null> {
    if (!hasActiveChallenge.value) {
      errorMessage.value = "请先点击 Start Challenge";
      return null;
    }

    if (!code.value.trim()) {
      errorMessage.value = "代码不能为空";
      return null;
    }

    busyAction.value = "submitting";
    errorMessage.value = "";

    try {
      // Submit 前必须重新测试当前代码。
      // 这样 Test Result 的 submission_digest 才和提交代码一致。
      const latestTest = await challengeApi.runTests({
        user_id: userId.value,
        session_id: sessionId.value,
        code: code.value,
        timeout_seconds: 3,
      });

      testResult.value = latestTest;

      if (
        latestTest.total === 0 ||
        latestTest.passed !== latestTest.total
      ) {
        failedAttempts.value += 1;
        errorMessage.value =
          `当前代码只通过 ${latestTest.passed}/${latestTest.total} 个测试，不能提交。`;

        return null;
      }

      const elapsedSeconds = startedAt.value
        ? Math.max(0, Math.floor((Date.now() - startedAt.value) / 1000))
        : 0;

      const result = await challengeApi.completeAssessment({
        user_id: userId.value,
        session_id: sessionId.value,
        submitted_code: code.value,
        elapsed_seconds: elapsedSeconds,
      });

      assessmentResult.value = result;
      return result;
    } catch (error) {
      errorMessage.value = getApiErrorMessage(error);
      return null;
    } finally {
      busyAction.value = "";
    }
  }

  function resetChallenge(): void {
    sessionId.value = "";
    challenge.value = null;
    code.value = "";
    testResult.value = null;
    hintResult.value = null;
    assessmentResult.value = null;
    failedAttempts.value = 0;
    startedAt.value = null;
    busyAction.value = "";
    errorMessage.value = "";
  }

  return {
    userId,
    sessionId,
    challenge,
    code,
    testResult,
    hintResult,
    assessmentResult,
    failedAttempts,
    busyAction,
    errorMessage,

    isBusy,
    hasActiveChallenge,
    allTestsPassed,

    setUserId,
    startChallenge,
    runTests,
    requestHint,
    submitAssessment,
    resetChallenge,
  };
})