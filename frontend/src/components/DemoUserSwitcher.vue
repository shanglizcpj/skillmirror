<script setup>
import { computed } from "vue"

import { useChallengeStore } from "../stores/challenge"


const challengeStore = useChallengeStore()


const demoUsers = [
  {
    id: "U-DEMO-BEGINNER-01",
    label: "User A",
    level: "Beginner",
    description: "初级学习者",
    color: "green",
  },
  {
    id: "U-DEMO-INTERMEDIATE-01",
    label: "User B",
    level: "Intermediate",
    description: "中级学习者",
    color: "blue",
  },
  {
    id: "U-DEMO-ADVANCED-01",
    label: "User C",
    level: "Advanced",
    description: "较强学习者",
    color: "purple",
  },
]


const currentUserId = computed(
  () => challengeStore.userId,
)


function selectDemoUser(user) {
  if (challengeStore.isBusy) {
    return
  }

  if (challengeStore.hasActiveChallenge) {
    const confirmed = window.confirm(
      "切换用户将关闭当前未完成的 Challenge，是否继续？",
    )

    if (!confirmed) {
      return
    }
  }

  challengeStore.resetChallenge()
  challengeStore.setUserId(user.id)
}
</script>


<template>
  <section class="demo-switcher">
    <div class="switcher-heading">
      <div>
        <p class="eyebrow">
          DEMO PROFILES
        </p>

        <h2>演示用户快速切换</h2>

        <p class="description">
          选择不同能力阶段的学习者，查看独立的
          Skill Mirror、Evidence 和 Report。
        </p>
      </div>

      <div class="current-user">
        <span>Current User</span>
        <strong>{{ currentUserId }}</strong>
      </div>
    </div>

    <div class="profile-grid">
      <button
        v-for="user in demoUsers"
        :key="user.id"
        type="button"
        class="profile-button"
        :class="[
          `profile-${user.color}`,
          {
            active: currentUserId === user.id,
          },
        ]"
        :disabled="challengeStore.isBusy"
        @click="selectDemoUser(user)"
      >
        <span class="profile-avatar">
          {{ user.label.slice(-1) }}
        </span>

        <span class="profile-copy">
          <strong>
            {{ user.label }} · {{ user.level }}
          </strong>

          <small>{{ user.description }}</small>

          <code>{{ user.id }}</code>
        </span>

        <span
          v-if="currentUserId === user.id"
          class="selected-mark"
        >
          已选择
        </span>

        <span
          v-else
          class="select-mark"
        >
          选择
        </span>
      </button>
    </div>
  </section>
</template>


<style scoped>
.demo-switcher {
  margin: 0 auto 24px;
  padding: 22px;
  border: 1px solid #dfe7f3;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 32px rgba(31, 48, 80, 0.08);
}

.switcher-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 18px;
}

.eyebrow {
  margin: 0 0 5px;
  color: #3568ff;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.14em;
}

.switcher-heading h2 {
  margin: 0;
  color: #101c35;
  font-size: 21px;
}

.description {
  margin: 7px 0 0;
  color: #71809b;
  font-size: 14px;
}

.current-user {
  min-width: 230px;
  padding: 11px 14px;
  border-radius: 12px;
  background: #f3f6fb;
}

.current-user span {
  display: block;
  margin-bottom: 3px;
  color: #8793aa;
  font-size: 12px;
}

.current-user strong {
  color: #172440;
  font-size: 14px;
}

.profile-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.profile-button {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 98px;
  padding: 14px;
  border: 2px solid transparent;
  border-radius: 14px;
  background: #f7f9fc;
  color: #172440;
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.profile-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 9px 20px rgba(34, 55, 90, 0.1);
}

.profile-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.profile-button.active {
  border-color: #3568ff;
  background: #f2f6ff;
}

.profile-avatar {
  display: grid;
  width: 42px;
  height: 42px;
  flex: 0 0 42px;
  place-items: center;
  border-radius: 50%;
  color: #ffffff;
  font-size: 17px;
  font-weight: 800;
}

.profile-green .profile-avatar {
  background: #14a673;
}

.profile-blue .profile-avatar {
  background: #3568ff;
}

.profile-purple .profile-avatar {
  background: #7548e8;
}

.profile-copy {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 3px;
}

.profile-copy strong {
  font-size: 14px;
}

.profile-copy small {
  color: #75829b;
  font-size: 12px;
}

.profile-copy code {
  overflow: hidden;
  color: #4b5d7d;
  font-size: 10px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.selected-mark,
.select-mark {
  position: absolute;
  top: 9px;
  right: 10px;
  font-size: 11px;
  font-weight: 800;
}

.selected-mark {
  color: #168255;
}

.select-mark {
  color: #8b96aa;
}

@media (max-width: 900px) {
  .profile-grid {
    grid-template-columns: 1fr;
  }

  .switcher-heading {
    flex-direction: column;
  }

  .current-user {
    width: 100%;
    box-sizing: border-box;
  }
}
</style>