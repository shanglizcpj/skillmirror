import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getSkills } from '../api/skillApi'

export const useSkillStore = defineStore('skill', () => {
  const skills = ref([])
  const loading = ref(false)
  const error = ref('')
  const loaded = ref(false)

  const measuredSkills = computed(() => {
    return skills.value.filter((skill) => skill.score !== null)
  })

  const overallScore = computed(() => {
    if (measuredSkills.value.length === 0) {
      return 0
    }

    const total = measuredSkills.value.reduce((sum, skill) => {
      return sum + skill.score
    }, 0)

    return Math.round(total / measuredSkills.value.length)
  })

  const averageConfidence = computed(() => {
    if (measuredSkills.value.length === 0) {
      return 0
    }

    const total = measuredSkills.value.reduce((sum, skill) => {
      return sum + skill.confidence
    }, 0)

    return Math.round(total / measuredSkills.value.length)
  })

  const evidenceCount = computed(() => {
    return skills.value.reduce((sum, skill) => {
      return sum + skill.evidence
    }, 0)
  })

  async function fetchSkills(forceRefresh = false) {
    if (loaded.value && !forceRefresh) {
      return
    }

    loading.value = true
    error.value = ''

    try {
      const response = await getSkills()

      skills.value = response.data.items || response.data || []
      loaded.value = true
    } catch (requestError) {
      skills.value = []
      error.value =
        requestError.userMessage ||
        requestError.message ||
        'Failed to load skill data.'
    } finally {
      loading.value = false
    }
  }

  function clearSkills() {
    skills.value = []
    loaded.value = true
  }

  return {
    skills,
    loading,
    error,
    loaded,
    measuredSkills,
    overallScore,
    averageConfidence,
    evidenceCount,
    fetchSkills,
    clearSkills
  }
})