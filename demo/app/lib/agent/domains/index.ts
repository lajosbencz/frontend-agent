import * as brewcraft from './brewcraft'
import * as emporium from './emporium'
import * as vendor from './vendor'

export const domainSessions = { brewcraft, emporium, vendor } as const
export type DomainKey = keyof typeof domainSessions
