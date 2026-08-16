import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

const ORIGINAL_CODE = `def find_max(nums):
    max_num = 0

    for i in range(len(nums) + 1):
        if nums[i] > max_num:
            max_num = nums[i]

    return max_num`

function readStoredVersions() {
  try {
    const storedValue =
      localStorage.getItem('skillmirror-code-versions')

    return storedValue
      ? JSON.parse(storedValue)
      : []
  } catch {
    return []
  }
}

export const useChallengeStore = defineStore(
  'challenge',
  () => {
    const currentCode = ref(
      localStorage.getItem('skillmirror-current-code') ||
        ORIGINAL_CODE
    )

    const versions = ref(readStoredVersions())

    const versionCount = computed(() => {
      return versions.value.length
    })

    const latestVersion = computed(() => {
      if (versions.value.length === 0) {
        return null
      }

      return versions.value[versions.value.length - 1]
    })

    function updateCode(newCode) {
      currentCode.value = newCode

      localStorage.setItem(
        'skillmirror-current-code',
        newCode
      )
    }

    function saveVersion(reason = 'manual') {
      const lastVersion =
        versions.value[versions.value.length - 1]

      if (
        lastVersion &&
        lastVersion.code === currentCode.value &&
        lastVersion.reason === reason
      ) {
        return lastVersion
      }

      const version = {
        id: crypto.randomUUID(),
        version: versions.value.length + 1,
        code: currentCode.value,
        reason,
        savedAt: new Date().toISOString()
      }

      versions.value.push(version)

      localStorage.setItem(
        'skillmirror-code-versions',
        JSON.stringify(versions.value)
      )

      return version
    }

    function resetCode() {
      updateCode(ORIGINAL_CODE)
      return saveVersion('reset')
    }

    function clearVersionHistory() {
      versions.value = []

      localStorage.removeItem(
        'skillmirror-code-versions'
      )
    }

    return {
      currentCode,
      versions,
      versionCount,
      latestVersion,
      updateCode,
      saveVersion,
      resetCode,
      clearVersionHistory
    }
  }
)