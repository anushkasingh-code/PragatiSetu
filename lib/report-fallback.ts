import { isProjectDeleted } from './projects';

export const FALLBACK_WBS_CODE = 'PIP-204-017';

export type FallbackReportRecord = {
  report_id: string;
  project_id?: string;
  filename: string;
  processing_status: string;
  created_at: string;
  isFallback: true;
};

export type FallbackCandidate = {
  activity_id: string;
  rank: number;
  overall_score: number;
};

export type FallbackReviewRecord = {
  event_id: string;
  report_id: string;
  project_id?: string;
  raw_text: string;
  identifier: string;
  action: string;
  object: string;
  location: string;
  status: string;
  decision: 'HUMAN_REVIEW';
  top_activity_id: string;
  match_confidence: number;
  reasons: string[];
  candidates: FallbackCandidate[];
  resolved: boolean;
};

export type FallbackMetrics = {
  humanReviewDelta: number;
  reportsDelta: number;
  eventsDelta: number;
};

const REVIEWS_KEY = 'pragati:fallback-reviews';
const REPORTS_KEY = 'pragati:fallback-reports';
const METRICS_KEY = 'pragati:fallback-metrics';

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown) {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(key, JSON.stringify(value));
}

export function generateFallbackReportId(): string {
  const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
  return `REP-DEMO-${stamp}-${Math.random().toString(36).slice(2, 6).toUpperCase()}`;
}

export function buildFallbackExtraction(reportId: string) {
  return {
    report_id: reportId,
    processing_status: 'PROCESSED' as const,
    event_count: 1,
    events: [{ event_id: `EVT-DEMO-${reportId.slice(-8)}` }],
  };
}

export function createFallbackReview(reportId: string, filename: string, projectId?: string): FallbackReviewRecord {
  const eventId = `EVT-DEMO-${reportId.slice(-8)}`;
  return {
    event_id: eventId,
    report_id: reportId,
    project_id: projectId,
    raw_text: `Supervisor field update: ${FALLBACK_WBS_CODE} spool erection completed at Rack B. Demo record synthesized from "${filename}" — original file did not match site report schema.`,
    identifier: FALLBACK_WBS_CODE,
    action: 'Completed',
    object: 'Spool Erection',
    location: 'Rack B Sector',
    status: 'COMPLETED',
    decision: 'HUMAN_REVIEW',
    top_activity_id: FALLBACK_WBS_CODE,
    match_confidence: 78,
    reasons: [
      'Deterministic demo fallback applied.',
      `Ambiguous match for WBS ${FALLBACK_WBS_CODE} — routed to human review.`,
    ],
    candidates: [
      { activity_id: FALLBACK_WBS_CODE, rank: 1, overall_score: 78 },
      { activity_id: 'PIP-204-018', rank: 2, overall_score: 62 },
    ],
    resolved: false,
  };
}

export function createFallbackReportRecord(reportId: string, filename: string, projectId?: string): FallbackReportRecord {
  return {
    report_id: reportId,
    project_id: projectId,
    filename,
    processing_status: 'PROCESSED',
    created_at: new Date().toISOString(),
    isFallback: true,
  };
}

export function persistFallbackReview(record: FallbackReviewRecord) {
  const existing = getFallbackReviews();
  writeJson(REVIEWS_KEY, [record, ...existing.filter((r) => r.event_id !== record.event_id)].slice(0, 50));
}

export function clearFallbackData(projectId?: string) {
  if (typeof window === 'undefined') return;
  try {
    if (!projectId) {
      sessionStorage.removeItem(REVIEWS_KEY);
      sessionStorage.removeItem(REPORTS_KEY);
      sessionStorage.removeItem(METRICS_KEY);
      return;
    }
    const reviews = getFallbackReviews().filter((r) => r.project_id && r.project_id !== projectId);
    writeJson(REVIEWS_KEY, reviews);
    const reports = getFallbackReports().filter((r) => r.project_id && r.project_id !== projectId);
    writeJson(REPORTS_KEY, reports);
    if (reviews.length === 0) {
      sessionStorage.removeItem(METRICS_KEY);
    }
  } catch {}
}

export function getFallbackReviews(projectId?: string): FallbackReviewRecord[] {
  if (projectId && isProjectDeleted(projectId)) return [];
  const alphaDeleted = isProjectDeleted('PROJ-ALPHA');
  return readJson<FallbackReviewRecord[]>(REVIEWS_KEY, []).filter((r) => {
    if (r.project_id && isProjectDeleted(r.project_id)) return false;
    if (!r.project_id && alphaDeleted) return false;
    if (projectId && r.project_id && r.project_id !== projectId) return false;
    return true;
  });
}

export function getPendingFallbackReviews(projectId?: string): FallbackReviewRecord[] {
  return getFallbackReviews(projectId).filter((r) => !r.resolved);
}

export function resolveFallbackReview(eventId: string) {
  const updated = getFallbackReviews().map((r) =>
    r.event_id === eventId ? { ...r, resolved: true } : r,
  );
  writeJson(REVIEWS_KEY, updated);
  const metrics = getFallbackMetrics();
  writeJson(METRICS_KEY, {
    ...metrics,
    humanReviewDelta: Math.max(0, metrics.humanReviewDelta - 1),
  });
}

export function persistFallbackReport(record: FallbackReportRecord) {
  const existing = getFallbackReports();
  writeJson(REPORTS_KEY, [record, ...existing.filter((r) => r.report_id !== record.report_id)].slice(0, 50));
}

export function getFallbackReports(projectId?: string): FallbackReportRecord[] {
  if (projectId && isProjectDeleted(projectId)) return [];
  const alphaDeleted = isProjectDeleted('PROJ-ALPHA');
  return readJson<FallbackReportRecord[]>(REPORTS_KEY, []).filter((r) => {
    if (r.project_id && isProjectDeleted(r.project_id)) return false;
    if (!r.project_id && alphaDeleted) return false;
    if (projectId && r.project_id && r.project_id !== projectId) return false;
    return true;
  });
}

export function incrementFallbackMetrics() {
  const metrics = getFallbackMetrics();
  writeJson(METRICS_KEY, {
    humanReviewDelta: metrics.humanReviewDelta + 1,
    reportsDelta: metrics.reportsDelta + 1,
    eventsDelta: metrics.eventsDelta + 1,
  });
}

export function getFallbackMetrics(): FallbackMetrics {
  return readJson<FallbackMetrics>(METRICS_KEY, {
    humanReviewDelta: 0,
    reportsDelta: 0,
    eventsDelta: 0,
  });
}

export function persistFallbackProcessing(reportId: string, filename: string, projectId?: string) {
  persistFallbackReview(createFallbackReview(reportId, filename, projectId));
  persistFallbackReport(createFallbackReportRecord(reportId, filename, projectId));
  incrementFallbackMetrics();
}

/** Deterministic delay for demo pipeline animation */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
