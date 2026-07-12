import { defineStore } from 'pinia'

export const useNavigationStore = defineStore('navigation', {
  state: () => ({
    lastAgentNavigation: null as string | null,
  }),
  actions: {
    recordAgentNavigation(path: string) {
      this.lastAgentNavigation = path
    },
  },
})
