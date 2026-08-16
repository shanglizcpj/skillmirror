<script setup>
const features = [
  {
    icon: '01',
    title: 'Complete Challenges',
    description: 'Solve practical Python programming challenges.'
  },
  {
    icon: '02',
    title: 'Collect Evidence',
    description: 'Your coding process becomes measurable skill evidence.'
  },
  {
    icon: '03',
    title: 'Update Your Mirror',
    description: 'Track your score, confidence and progress over time.'
  }
]
</script>

<template>
  <section class="home-page">
    <div class="hero-section">
      <div class="hero-content">
        <div class="eyebrow">AI-POWERED SKILL ASSESSMENT</div>

        <h1>
          See how you solve problems,
          <span>not just your final answer.</span>
        </h1>

        <p class="hero-description">
          SkillMirror observes your coding process, verifies your performance
          and builds an evidence-driven digital twin of your programming skills.
        </p>

        <div class="hero-actions">
          <router-link to="/challenge" class="primary-button">
            Start Assessment
          </router-link>

          <router-link to="/skills" class="secondary-button">
            View Skill Mirror
          </router-link>
        </div>

        <div class="hero-stats">
          <div>
            <strong>5</strong>
            <span>Core Skills</span>
          </div>

          <div>
            <strong>18</strong>
            <span>Evidence Items</span>
          </div>

          <div>
            <strong>72%</strong>
            <span>Overall Confidence</span>
          </div>
        </div>
      </div>

      <div class="profile-card">
        <div class="profile-top">
          <div class="large-avatar">CZ</div>

          <div>
            <span class="small-label">CURRENT LEARNER</span>
            <h2>Chenpeiji Zhang</h2>
            <p>Software Engineering Student</p>
          </div>
        </div>

        <div class="profile-progress">
          <div class="progress-heading">
            <span>Assessment progress</span>
            <strong>62%</strong>
          </div>

          <div class="progress-track">
            <div class="progress-fill" style="width: 62%"></div>
          </div>
        </div>

        <div class="profile-status">
          <span class="status-dot"></span>
          Next focus: Debugging
        </div>
      </div>
    </div>

    <div class="section-heading">
      <span>HOW IT WORKS</span>
      <h2>Build your skill mirror in three steps</h2>
    </div>

    <div class="feature-grid">
      <article
        v-for="feature in features"
        :key="feature.title"
        class="feature-card"
      >
        <div class="feature-number">{{ feature.icon }}</div>
        <h3>{{ feature.title }}</h3>
        <p>{{ feature.description }}</p>
      </article>
    </div>
  </section>
</template>