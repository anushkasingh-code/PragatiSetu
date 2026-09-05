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
