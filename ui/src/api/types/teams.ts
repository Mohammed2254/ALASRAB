/** الأسراب والعضويات — `schemas/teams.py`. */
import type { Count } from '../brand'

export type AdminTeamRow = {
  id: Count
  name: string
  code: string
  archived_at: string | null
  active_members: Count
}

export type Teams = { teams: AdminTeamRow[] }
export type CreateTeamForm = { name: string; code: string }
export type CreatedTeam = { id: Count; name: string; code: string }
export type ArchivedTeam = { id: Count; archived_at: string }
export type TransferredMember = { user_id: Count; team_id: Count; role: string }
