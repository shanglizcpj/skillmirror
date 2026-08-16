import {
  createRouter,
  createWebHistory
} from 'vue-router'

const routes = [
  {
    path: '/',
    name: 'home',
    component: () => import('../views/HomeView.vue'),
    meta: {
      title: 'Home'
    }
  },
  {
    path: '/skills',
    name: 'skills',
    component: () => import('../views/SkillMirrorView.vue'),
    meta: {
      title: 'Skill Mirror'
    }
  },
  {
    path: '/challenge',
    name: 'challenge',
    component: () => import('../views/ChallengeView.vue'),
    meta: {
      title: 'Challenge'
    }
  },
  {
    path: '/report',
    name: 'report',
    component: () => import('../views/ReportView.vue'),
    meta: {
      title: 'Skill Report'
    }
  },
  {
    path: '/evidence',
    name: 'evidence',
    component: () => import('../views/EvidenceView.vue'),
    meta: {
      title: 'Evidence'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/NotFoundView.vue'),
    meta: {
      title: 'Page Not Found'
    }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return {
      top: 0
    }
  }
})

router.afterEach((to) => {
  document.title = `${to.meta.title || 'SkillMirror'} | SkillMirror`
})

export default router