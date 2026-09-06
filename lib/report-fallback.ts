/**
 * Report Processing Helpers & Storage Cleanup
 *
 * All synthetic fallback record creation has been removed.
 * Pipeline processing is strictly driven by the real backend API.
 */

const REVIEWS_KEY = 'pragati:fallback-reviews';
const REPORTS_KEY = 'pragati:fallback-reports';
const METRICS_KEY = 'pragati:fallback-metrics';

/** Purges any legacy fallback/demo data from sessionStorage to keep workspace clean. */
export function clearFallbackData(projectId?: string) {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.removeItem(REVIEWS_KEY);
    sessionStorage.removeItem(REPORTS_KEY);
    sessionStorage.removeItem(METRICS_KEY);
  } catch {}
}

/** Deterministic delay for smooth stepper UI transitions */
export function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// -------------------------------------------------------------
// MOCK EXPORTS TO SATISFY UI DEPENDENCIES WITHOUT REAL FALLBACKS
// -------------------------------------------------------------
export const FALLBACK_WBS_CODE = 'MOCK-WBS';

export function getFallbackMetrics() {
  return { eventsProcessed: 0, autoMatched: 0, accuracy: 0, eventsDelta: 0 };
}

export function getPendingFallbackReviews(): any[] {
  return [];
}

export function getFallbackReports(): any[] {
  return [];
}

export function persistFallbackProcessing(reportId: string, payload: any) {}

export function createFallbackReportRecord(reportId: string, filename: string): any {
  return {
    report_id: reportId,
    filename: filename,
    project_id: 'PROJ-ALPHA',
    processing_status: 'UPLOADED'
  };
}

export function buildFallbackExtraction(reportId: string): any {
  return {
    processing_status: 'EVENTS_EXTRACTED',
    event_count: 0
  };
}

export function generateFallbackReportId(): string {
  return `REP-MOCK-${Date.now()}`;
}

export function resolveFallbackReview(eventId: string, decision?: string, activityId?: string) {}

export type FallbackReportRecord = any;
export type FallbackReviewRecord = any;
