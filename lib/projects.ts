export const DELETED_PROJECTS_KEY = 'pragatisetu:deleted_projects';

/**
 * Isolated demo fixtures for offline tests and sample references.
 * MUST NOT be used as an automatic fallback when the live /projects API fails or returns empty.
 */
export const DEMO_PROJECT_FIXTURES = [
  { name: 'Project Alpha', code: 'PROJ-ALPHA', displayCode: '24P201', status: 'Operational', progress: 31.3 },
  { name: 'Project Beta', code: 'PROJ-BETA', displayCode: 'PROJ-BETA', status: 'Planning', progress: 0.0 },
];
export const FALLBACK_PROJECTS = DEMO_PROJECT_FIXTURES;

export function getDeletedProjectCodes(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw = localStorage.getItem(DELETED_PROJECTS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? new Set(parsed) : new Set();
    }
    // One-time migration of legacy keys to single canonical key
    const legacyRaw = localStorage.getItem('deleted_project_codes') || localStorage.getItem('deletedProjectCodes');
    if (legacyRaw) {
      const legacyParsed = JSON.parse(legacyRaw);
      const set = Array.isArray(legacyParsed) ? new Set<string>(legacyParsed) : new Set<string>();
      localStorage.setItem(DELETED_PROJECTS_KEY, JSON.stringify(Array.from(set)));
      localStorage.removeItem('deleted_project_codes');
      localStorage.removeItem('deletedProjectCodes');
      return set;
    }
    return new Set();
  } catch {
    return new Set();
  }
}

export function recordDeletedProjectCode(code: string) {
  if (typeof window === 'undefined') return;
  try {
    const set = getDeletedProjectCodes();
    set.add(code);
    localStorage.setItem(DELETED_PROJECTS_KEY, JSON.stringify(Array.from(set)));
  } catch {}
}

export function unrecordDeletedProjectCode(code: string) {
  if (typeof window === 'undefined') return;
  try {
    const set = getDeletedProjectCodes();
    set.delete(code);
    localStorage.setItem(DELETED_PROJECTS_KEY, JSON.stringify(Array.from(set)));
  } catch {}
}

export function isProjectDeleted(code: string): boolean {
  return getDeletedProjectCodes().has(code);
}
