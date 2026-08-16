<script setup>
defineProps({
  type: {
    type: String,
    default: 'loading'
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    default: ''
  }
})

defineEmits(['retry'])
</script>

<template>
  <div class="state-panel">
    <div
      v-if="type === 'loading'"
      class="loading-spinner"
    ></div>

    <div
      v-else-if="type === 'error'"
      class="state-icon error-icon"
    >
      !
    </div>

    <div
      v-else
      class="state-icon empty-icon"
    >
      ○
    </div>

    <h2>
      {{
        title ||
        (type === 'loading'
          ? 'Loading'
          : type === 'error'
            ? 'Something went wrong'
            : 'No data yet')
      }}
    </h2>

    <p>
      {{
        message ||
        (type === 'loading'
          ? 'Please wait while we load your skill data.'
          : type === 'error'
            ? 'The requested data could not be loaded.'
            : 'Complete a challenge to collect your first evidence.')
      }}
    </p>

    <button
      v-if="type === 'error'"
      class="primary-button"
      @click="$emit('retry')"
    >
      Try Again
    </button>

    <router-link
      v-if="type === 'empty'"
      to="/challenge"
      class="primary-button"
    >
      Start Challenge
    </router-link>
  </div>
</template>