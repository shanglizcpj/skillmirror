<script setup>
import {
  computed,
  onMounted,
  onUnmounted,
  ref
} from 'vue'

import { storeToRefs } from 'pinia'

import MonacoCodeEditor from
  '../components/MonacoCodeEditor.vue'

import { useChallengeStore } from
  '../stores/challengeStore'

const challengeStore = useChallengeStore()

const {
  currentCode: code,
  versions,
  versionCount
} = storeToRefs(challengeStore)

const consoleOutput = ref(
  'Ready. Press Ctrl + Enter or click Run.'
)

const testStatus = ref('Not run')
const hintLevel = ref(0)
const elapsedSeconds = ref(0)
const noticeMessage = ref('')
const allTestsPassed = ref(false)

const tests = ref([
  {
    id: 1,
    name: 'Positive numbers',
    status: 'pending'
  },
  {
    id: 2,
    name: 'Mixed numbers',
    status: 'pending'
  },
  {
    id: 3,
    name: 'Negative numbers',
    status: 'pending'
  },
  {
    id: 4,
    name: 'Boundary index',
    status: 'pending'
  },
  {
    id: 5,
    name: 'Single element',
    status: 'pending'
  }
])

let timer = null
let noticeTimer = null

const formattedTime = computed(() => {
  const minutes = Math.floor(
    elapsedSeconds.value / 60
  )

  const seconds =
    elapsedSeconds.value % 60

  return `${String(minutes).padStart(2, '0')}:${String(
    seconds
  ).padStart(2, '0')}`
})

const recentVersions = computed(() => {
  return [...versions.value]
    .reverse()
    .slice(0, 4)
})

function showNotice(message) {
  noticeMessage.value = message

  clearTimeout(noticeTimer)

  noticeTimer = setTimeout(() => {
    noticeMessage.value = ''
  }, 2500)
}

function updateCode(newCode) {
  challengeStore.updateCode(newCode)
}

function setTestResults(statuses) {
  tests.value = tests.value.map((test, index) => ({
    ...test,
    status: statuses[index]
  }))

  const passedCount = tests.value.filter(
    (test) => test.status === 'passed'
  ).length

  testStatus.value = `${passedCount} / ${tests.value.length} passed`
  allTestsPassed.value =
    passedCount === tests.value.length
}

function runCode() {
  const savedVersion =
    challengeStore.saveVersion('run')

  const currentValue = code.value.trim()

  if (
    currentValue === '' ||
    !currentValue.includes('def find_max')
  ) {
    consoleOutput.value =
      'SyntaxError: expected function "find_max".'

    setTestResults([
      'failed',
      'failed',
      'failed',
      'failed',
      'failed'
    ])

    showNotice(
      `Version ${savedVersion.version} saved`
    )

    return
  }

  const hasBoundaryBug =
    currentValue.includes(
      'range(len(nums) + 1)'
    ) ||
    currentValue.includes(
      'range(len(nums)+1)'
    )

  const hasNegativeBug =
    currentValue.includes('max_num = 0') ||
    currentValue.includes('max_num=0')

  if (hasBoundaryBug) {
    consoleOutput.value =
      'Traceback (most recent call last):\n' +
      '  File "solution.py", line 4\n' +
      'IndexError: list index out of range'

    setTestResults([
      'failed',
      'failed',
      'failed',
      'failed',
      'failed'
    ])
  } else if (hasNegativeBug) {
    consoleOutput.value =
      'Execution completed.\n\n' +
      'AssertionError: expected -3, but received 0.\n' +
      'Some hidden tests did not pass.'

    setTestResults([
      'passed',
      'passed',
      'failed',
      'passed',
      'passed'
    ])
  } else {
    consoleOutput.value =
      'Execution completed successfully.\n\n' +
      'All 5 tests passed.\n' +
      'Runtime: 0.03 seconds'

    setTestResults([
      'passed',
      'passed',
      'passed',
      'passed',
      'passed'
    ])
  }

  showNotice(
    `Version ${savedVersion.version} saved and executed`
  )
}

function requestHint() {
  hintLevel.value += 1

  const currentValue = code.value

  if (
    currentValue.includes(
      'range(len(nums) + 1)'
    )
  ) {
    if (hintLevel.value === 1) {
      consoleOutput.value =
        'Hint Level 1:\n' +
        'Check how many valid indexes a list of length n has.'
    } else if (hintLevel.value === 2) {
      consoleOutput.value =
        'Hint Level 2:\n' +
        'Compare range(len(nums)) with range(len(nums) + 1).'
    } else {
      consoleOutput.value =
        'Hint Level 3:\n' +
        'The loop should not access nums[len(nums)].'
    }
  } else {
    consoleOutput.value =
      'Hint:\n' +
      'Think about whether zero is always a safe initial maximum value.'
  }
}

function saveManualVersion() {
  const version =
    challengeStore.saveVersion('manual')

  showNotice(
    `Version ${version.version} saved`
  )
}

function submitChallenge() {
  const version =
    challengeStore.saveVersion('submit')

  if (!allTestsPassed.value) {
    consoleOutput.value =
      'Submission blocked.\n\n' +
      'Please run your code and pass all tests before submitting.'

    showNotice(
      `Version ${version.version} saved, but tests are incomplete`
    )

    return
  }

  consoleOutput.value =
    'Challenge submitted successfully.\n\n' +
    'Your final code and version history have been recorded.\n' +
    'The Evaluator will analyze your problem-solving process.'

  testStatus.value = 'Submitted'

  showNotice(
    `Version ${version.version} submitted`
  )
}

function resetCode() {
  const version =
    challengeStore.resetCode()

  consoleOutput.value =
    'Code reset to the original challenge version.'

  testStatus.value = 'Not run'
  hintLevel.value = 0
  allTestsPassed.value = false

  tests.value = tests.value.map((test) => ({
    ...test,
    status: 'pending'
  }))

  showNotice(
    `Original code restored as Version ${version.version}`
  )
}

function formatVersionTime(dateValue) {
  return new Date(dateValue).toLocaleTimeString(
    [],
    {
      hour: '2-digit',
      minute: '2-digit'
    }
  )
}

onMounted(() => {
  timer = setInterval(() => {
    elapsedSeconds.value += 1
  }, 1000)
})

onUnmounted(() => {
  clearInterval(timer)
  clearTimeout(noticeTimer)
})
</script>

<template>
  <section class="challenge-page">
    <div
      v-if="noticeMessage"
      class="editor-notice"
    >
      {{ noticeMessage }}
    </div>

    <div class="challenge-topbar">
      <div>
        <span class="eyebrow">
          DEBUGGING CHALLENGE 01
        </span>

        <h1>Fix the Maximum Finder</h1>
      </div>

      <div class="challenge-meta">
        <div>
          <span>Progress</span>
          <strong>1 / 5</strong>
        </div>

        <div>
          <span>Timer</span>
          <strong>{{ formattedTime }}</strong>
        </div>

        <div>
          <span>Versions</span>
          <strong>{{ versionCount }}</strong>
        </div>
      </div>
    </div>

    <div class="workspace-grid">
      <aside
        class="workspace-panel challenge-description"
      >
        <div class="panel-title">
          <span>Challenge</span>
          <span class="difficulty-badge">
            Beginner
          </span>
        </div>

        <h2>Find and fix the bugs</h2>

        <p>
          The function should return the largest
          number from a non-empty list.
        </p>

        <h3>Requirements</h3>

        <ul>
          <li>
            Do not access an invalid list index.
          </li>

          <li>
            Support lists containing only negative
            numbers.
          </li>

          <li>
            Keep the function name unchanged.
          </li>
        </ul>

        <div class="example-box">
          <span>Expected result</span>

          <code>
            find_max([-8, -3, -5]) → -3
          </code>
        </div>
      </aside>

      <main class="workspace-panel editor-panel">
        <div class="panel-title">
          <span>Code Editor</span>

          <div class="editor-header-info">
            <span>Python 3</span>
            <span>Version {{ versionCount }}</span>
          </div>
        </div>

        <MonacoCodeEditor
          :model-value="code"
          language="python"
          @update:model-value="updateCode"
          @run="runCode"
          @submit="submitChallenge"
        />

        <div class="editor-shortcuts">
          <span>Ctrl + Enter: Run</span>
          <span>Ctrl + Shift + Enter: Submit</span>
        </div>

        <div class="editor-actions">
          <button
            class="secondary-button"
            @click="resetCode"
          >
            Reset
          </button>

          <button
            class="secondary-button"
            @click="saveManualVersion"
          >
            Save Version
          </button>

          <button
            class="run-button"
            @click="runCode"
          >
            Run
          </button>

          <button
            class="primary-button"
            @click="submitChallenge"
          >
            Submit
          </button>
        </div>
      </main>

      <aside class="workspace-panel coach-panel">
        <div class="panel-title">
          <span>AI Coach</span>
          <span class="online-indicator">
            Online
          </span>
        </div>

        <div class="coach-message">
          <div class="coach-avatar">AI</div>

          <p>
            Run the code first. I will give
            progressive hints without revealing
            the complete solution.
          </p>
        </div>

        <button
          class="hint-button"
          @click="requestHint"
        >
          Ask for Hint
        </button>

        <p class="hint-counter">
          Hint level used: {{ hintLevel }}
        </p>

        <div class="version-history">
          <h3>Recent versions</h3>

          <div
            v-if="recentVersions.length === 0"
            class="version-empty"
          >
            No saved versions yet.
          </div>

          <div
            v-for="version in recentVersions"
            :key="version.id"
            class="version-item"
          >
            <div>
              <strong>
                Version {{ version.version }}
              </strong>

              <span>{{ version.reason }}</span>
            </div>

            <time>
              {{ formatVersionTime(version.savedAt) }}
            </time>
          </div>
        </div>

        <div class="coach-note">
          Code changes, execution results and hint
          usage will become assessment evidence.
        </div>
      </aside>
    </div>

    <div class="result-grid">
      <div class="result-panel">
        <div class="panel-title">
          <span>Console</span>
          <span>Latest execution</span>
        </div>

        <pre>{{ consoleOutput }}</pre>
      </div>

      <div class="result-panel">
        <div class="panel-title">
          <span>Test Result</span>
          <strong>{{ testStatus }}</strong>
        </div>

        <div class="test-list">
          <div
            v-for="test in tests"
            :key="test.id"
            :class="{
              'test-passed':
                test.status === 'passed',
              'test-failed':
                test.status === 'failed',
              'test-pending':
                test.status === 'pending'
            }"
          >
            <span v-if="test.status === 'passed'">
              ✓
            </span>

            <span v-else-if="test.status === 'failed'">
              ✕
            </span>

            <span v-else>○</span>

            {{ test.name }}
          </div>
        </div>
      </div>
    </div>
  </section>
</template>