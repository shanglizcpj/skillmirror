import http from './http'
import { mockSkills } from '../mock/skills'

const useMock = import.meta.env.VITE_USE_MOCK === 'true'

function wait(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds)
  })
}

export async function getSkills() {
  if (useMock) {
    await wait(700)

    return {
      data: {
        items: mockSkills
      }
    }
  }

  return http.get('/skills')
}

export async function getSkillById(skillId) {
  if (useMock) {
    await wait(400)

    const skill = mockSkills.find((item) => item.id === skillId)

    return {
      data: skill
    }
  }

  return http.get(`/skills/${skillId}`)
}