<script setup>
const changes = [
  {
    title: 'Error Identification',
    description: 'You identified the IndexError after the first execution.',
    change: '+8',
    type: 'positive'
  },
  {
    title: 'Boundary Awareness',
    description: 'You corrected the loop boundary and passed the hidden test.',
    change: '+7',
    type: 'positive'
  },
  {
    title: 'Hint Dependency',
    description: 'You used one Level-1 hint during the challenge.',
    change: '-1',
    type: 'negative'
  }
]
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">ASSESSMENT COMPLETE</span>
        <h1>Skill Report</h1>
        <p>
          Your updated score is based on verified behavior from this challenge.
        </p>
      </div>

      <router-link to="/evidence" class="primary-button">
        View Evidence
      </router-link>
    </div>

    <div class="score-change-card">
      <div class="score-block">
        <span>Before</span>
        <strong>63</strong>
        <small>Debugging</small>
      </div>

      <div class="score-arrow">
        <span>+11</span>
        <div>→</div>
      </div>

      <div class="score-block score-after">
        <span>After</span>
        <strong>74</strong>
        <small>Debugging</small>
      </div>
    </div>

    <div class="report-layout">
      <div class="report-card">
        <div class="section-heading left">
          <span>SCORE EXPLANATION</span>
          <h2>Why did my score change?</h2>
        </div>

        <div class="change-list">
          <article
            v-for="item in changes"
            :key="item.title"
            class="change-item"
          >
            <div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.description }}</p>
            </div>

            <strong :class="item.type">
              {{ item.change }}
            </strong>
          </article>
        </div>
      </div>

      <aside class="report-card confidence-card">
        <span class="small-label">CONFIDENCE</span>
        <div class="confidence-value">87%</div>

        <div class="progress-track">
          <div class="progress-fill" style="width: 87%"></div>
        </div>

        <p>
          High confidence because the result was verified through multiple
          hidden tests and process evidence.
        </p>

        <router-link to="/challenge" class="secondary-button full-button">
          Next Challenge
        </router-link>
      </aside>
    </div>
  </section>
</template>