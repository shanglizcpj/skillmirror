<script setup>
const evidenceItems = [
  {
    time: '10:21',
    title: 'Identified IndexError',
    description: 'Detected an invalid list index after executing the code.',
    skill: 'Error Identification',
    score: '+8',
    strength: 'Strong'
  },
  {
    time: '10:25',
    title: 'Fixed boundary condition',
    description: 'Changed the loop range and passed the boundary test.',
    skill: 'Boundary Awareness',
    score: '+7',
    strength: 'Strong'
  },
  {
    time: '10:28',
    title: 'Used Level-1 Hint',
    description: 'Requested a general conceptual hint from the AI Coach.',
    skill: 'Hint Dependency',
    score: '-1',
    strength: 'Medium'
  },
  {
    time: '10:34',
    title: 'Passed all hidden tests',
    description: 'The final submission passed all five verification tests.',
    skill: 'Fix Verification',
    score: '+4',
    strength: 'Strong'
  }
]
</script>

<template>
  <section>
    <div class="page-heading">
      <div>
        <span class="eyebrow">VERIFIED LEARNING HISTORY</span>
        <h1>Evidence Timeline</h1>
        <p>
          Every skill update is connected to observable and explainable evidence.
        </p>
      </div>

      <div class="date-badge">August 14, 2026</div>
    </div>

    <div class="evidence-summary">
      <div>
        <span>Skill</span>
        <strong>Debugging</strong>
      </div>

      <div>
        <span>Score Change</span>
        <strong>63 → 74</strong>
      </div>

      <div>
        <span>Evidence Items</span>
        <strong>4</strong>
      </div>

      <div>
        <span>Confidence</span>
        <strong>87%</strong>
      </div>
    </div>

    <div class="timeline">
      <article
        v-for="item in evidenceItems"
        :key="item.title"
        class="timeline-item"
      >
        <div class="timeline-time">{{ item.time }}</div>

        <div class="timeline-marker"></div>

        <div class="timeline-card">
          <div class="timeline-card-header">
            <div>
              <span class="evidence-skill">{{ item.skill }}</span>
              <h3>{{ item.title }}</h3>
            </div>

            <strong
              :class="item.score.startsWith('+') ? 'positive' : 'negative'"
            >
              {{ item.score }}
            </strong>
          </div>

          <p>{{ item.description }}</p>

          <span class="strength-badge">
            {{ item.strength }} Evidence
          </span>
        </div>
      </article>
    </div>
  </section>
</template>