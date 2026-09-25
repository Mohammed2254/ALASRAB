/** اللوحات — `GET /boards/{pilots,teams,formation}`. */
import { request } from '../client'
import type { Formation, FormationScope, PilotRow, TeamBoardRow } from '../types/boards'

export const boardsApi = {
  pilots: () => request<{ pilots: PilotRow[] }>('/boards/pilots'),
  teams: () => request<{ teams: TeamBoardRow[] }>('/boards/teams'),
  formation: (scope: FormationScope = 'team') =>
    request<Formation>(`/boards/formation?scope=${scope}`),
}
