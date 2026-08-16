<script setup>
import { onMounted } from 'vue'
import { storeToRefs } from 'pinia'

import StatePanel from '../components/StatePanel.vue'
import { useSkillStore } from '../stores/skillStore'

const skillStore = useSkillStore()

const {
  skills,
  loading,
  error,
  overallScore,
  averageConfidence,
  evidenceCount,
  measuredSkills
} = storeToRefs(skillStore)

function refreshSkills() {
  skillStore.fetchSkills(true)
}

onMounted(() => {
  skillStore.fetchSkills()
})
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">YOUR DIGITAL SKILL TWIN</span>
        <h1>Skill Mirror</h1>

        <p>
          Each score is supported by observed behavior and verified evidence.
        </p>
      </div>

      <div class="page-heading-actions">
        <button
          class="secondary-button"
          :disabled="loading"
          @click="refreshSkills"
        >
          Refresh
        </button>

        <router-link
          to="/challenge"
          class="primary-button"
        >
          Continue Assessment
        </router-link>
      </div>
    </div>

    <StatePanel
      v-if="loading"
      type="loading"
    />

    <StatePanel
      v-else-if="error"
      type="error"
      title="Unable to load Skill Mirror"
      :message="error"
      @retry="refreshSkills"
    />

    <StatePanel
      v-else-if="skills.length === 0"
      type="empty"
      title="Your Skill Mirror is empty"
      message="Complete your first challenge to generate verified skill evidence."
    />

    <template v-else>
      <div class="summary-grid">
        <div class="summary-card">
          <span>Overall Score</span>
          <strong>{{ overallScore }}</strong>
          <small>Developing</small>
        </div>

        <div class="summary-card">
          <span>Average Confidence</span>
          <strong>{{ averageConfidence }}%</strong>
          <small>
            Based on {{ measuredSkills.length }} measured skills
          </small>
        </div>

        <div class="summary-card">
          <span>Evidence Collected</span>
          <strong>{{ evidenceCount }}</strong>
          <small>Verified behavior records</small>
        </div>
      </div>

      <div class="skill-list">
        <article
          v-for="skill in skills"
          :key="skill.id"
          class="skill-card"
        >
          <div
            class="skill-color"
            :style="{ backgroundColor: skill.color }"
          ></div>

          <div class="skill-main">
            <div class="skill-title-row">
              <div>
                <h3>{{ skill.name }}</h3>
                <span>
                  {{ skill.evidence }} evidence items
                </span>
              </div>

              <div class="skill-score">
                {{ skill.score === null ? '?' : skill.score }}
              </div>
            </div>

            <div class="skill-bar">
              <div
                class="skill-bar-fill"
                :style="{
                  width: `${skill.score ?? 4}%`,
                  backgroundColor: skill.color
                }"
              ></div>
            </div>

            <div class="skill-footer">
              <span>
                Confidence:
                <strong>
                  {{
                    skill.confidence === 0
                      ? 'Not measured'
                      : `${skill.confidence}%`
                  }}
                </strong>
              </span>

              <span class="trend-badge">
                {{
                  skill.trend === null
                    ? 'New'
                    : `+${skill.trend}`
                }}
              </span>
            </div>
          </div>
        </article>
      </div>
    </template>
  </section>
</template> 