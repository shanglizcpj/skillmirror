<script setup>
import AppHeader from './components/AppHeader.vue'
import AppFooter from './components/AppFooter.vue'
import DemoIdentityNotice from './components/DemoIdentityNotice.vue'
</script>

<template>
  <div class="app-shell">
    <AppHeader />

    <main class="page-container">
      <DemoIdentityNotice />

      <router-view v-slot="{ Component }">
        <transition
          name="page"
          mode="out-in"
        >
          <component :is="Component" />
        </transition>
      </router-view>
    </main>

    <AppFooter />
  </div>
</template>