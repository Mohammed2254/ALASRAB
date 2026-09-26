/** سجلّ التدقيق («الصندوق الأسود») — `schemas/audit_log.py` (FR-084). */
import type { Count } from '../brand'

export type AuditEntry = { id: Count; kind: string; summary: string; actor_name: string; at: string }
export type AuditLog = { entries: AuditEntry[] }
