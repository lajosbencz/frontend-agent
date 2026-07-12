import type { Session } from 'frontend-agent'
import { onEngineReset } from './engine'

/** Memoize a domain's Session builder; auto-invalidates when the shared engine resets (backend switch). */
export function memoizedSession(build: () => Promise<Session>) {
  let promise: Promise<Session> | null = null
  onEngineReset(() => {
    promise = null
  })
  return {
    get: () => (promise ??= build()),
    reset: () => {
      promise = null
    },
  }
}
