export const DELETED_PROJECTS_KEY = 'pragatisetu:deleted_projects';

export const FALLBACK_PROJECTS = [
  { name: 'Project Alpha', code: 'PROJ-ALPHA', displayCode: '24P201', status: 'Operational', progress: 31.3 },
  { name: 'Project Beta', code: 'PROJ-BETA', displayCode: 'PROJ-BETA', status: 'Planning', progress: 0.0 },
];

export function getDeletedProjectCodes(): Set<string> {
  if (typeof window === 'undefined') return new Set();
  try {
    const raw =
      localStorage.getItem(DELETED_PROJECTS_KEY) ||
      localStorage.getItem('deleted_project_codes') ||
      localStorage.getItem('deletedProjectCodes');
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? new Set(parsed) : new Set();
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
