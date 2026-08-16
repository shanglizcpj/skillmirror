<template>
  <header class="app-header">
    <router-link to="/" class="brand">
      <div class="brand-logo">S</div>

      <div>
        <div class="brand-name">SkillMirror</div>
        <div class="brand-subtitle">Evidence-Driven Assessment</div>
      </div>
    </router-link>

    <nav class="nav-links">
      <router-link to="/">Home</router-link>
      <router-link to="/skills">Skill Mirror</router-link>
      <router-link to="/challenge">Challenge</router-link>
      <router-link to="/report">Report</router-link>
      <router-link to="/evidence">Evidence</router-link>
    </nav>

    <div class="header-user">
      <div class="user-avatar">CZ</div>

      <div>
        <strong>Chenpeiji</strong>
        <span>Python Learner</span>
      </div>
    </div>
  </header>
</template>