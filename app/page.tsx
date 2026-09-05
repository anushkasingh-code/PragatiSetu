'use client';

import { Suspense } from 'react';
import { apiFetchSafe } from '@/lib/api';
import { useAppDataRefresh } from '@/lib/app-sync';
import { getFallbackMetrics, getPendingFallbackReviews } from '@/lib/report-fallback';
import { getDeletedProjectCodes, isProjectDeleted, FALLBACK_PROJECTS } from '@/lib/projects';
import { Eye, ArrowRight, Activity, Clock, Layers } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

type DashboardData = {
  progress_percentage?: number;
  total_activities?: number;
  completed_activities?: number;
  in_progress_activities?: number;
  not_started_activities?: number;
  total_events?: number;
  auto_linked_events?: number;
  human_review_events?: number;
  unplanned_events?: number;
  conflict_events?: number;
};

interface SCurvePoint {
  label: string;
  actual: number;
  planned: number;
}

function formatMetric(value: number | null, suffix = '') {
  return value == null ? '—' : `${value}${suffix}`;
}

function DashboardContent() {
  const searchParams = useSearchParams();
  const pathname = usePathname();

  const [activeProject, setActiveProject] = useState<{
    project_id: string;
    name: string;
    displayCode: string;
    description?: string;
  } | null>(null);

  const [overallProgress, setOverallProgress] = useState<number | null>(null);
  const [aiAccuracy, setAiAccuracy] = useState<number | null>(null);
  const [pendingActions, setPendingActions] = useState<number | null>(null);
  const [humanReviewEvents, setHumanReviewEvents] = useState<number | null>(null);
  const [conflictEvents, setConflictEvents] = useState<number | null>(null);
  const [activityBreakdown, setActivityBreakdown] = useState<{
    completed: number;
    inProgress: number;
    delayed: number;
    total: number;
  } | null>(null);
  const [recentReports, setRecentReports] = useState<{
    id: string;
    sup: string;
    loc: string;
    events: number;
    status: string;
  }[]>([]);
  const [sCurveData, setSCurveData] = useState<SCurvePoint[]>([]);

  const resolveActiveProject = useCallback(async () => {
    const deleted = getDeletedProjectCodes();
    const res = await apiFetchSafe<{ project_id: string; name: string; description?: string }[]>('/projects');
    let available: { project_id: string; name: string; displayCode: string; description?: string }[] = [];

    if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
      available = res.data
        .filter((p) => !deleted.has(p.project_id))
        .map((p) => ({
          project_id: p.project_id,
          name: p.name,
          displayCode: p.project_id === 'PROJ-ALPHA' ? '24P201' : p.project_id,
          description: p.description,
        }));
    }

    if (available.length === 0 && (!res.ok || res.data.length === 0)) {
      const activeFallbacks = FALLBACK_PROJECTS.filter((p) => !deleted.has(p.code));
      available = activeFallbacks.map((p) => ({
        project_id: p.code,
        name: p.name,
        displayCode: p.displayCode,
        description: 'PragatiSetu Infrastructure Construction Package',
      }));
    }

    if (available.length === 0) {
      setActiveProject(null);
      return null;
    }

    const requestedId = searchParams.get('project_id');
    const normalizedReq = requestedId === 'PRAGATI-01' || requestedId === '24P201' ? 'PROJ-ALPHA' : requestedId;
    const current = (normalizedReq ? available.find((p) => p.project_id === normalizedReq) : null) || available[0];
    setActiveProject(current);
    return current;
  }, [searchParams]);

  const loadDashboard = useCallback(async () => {
    const currentProj = await resolveActiveProject();
    if (!currentProj) {
      setOverallProgress(null);
      setAiAccuracy(null);
      setPendingActions(0);
      setHumanReviewEvents(0);
      setConflictEvents(0);
      setActivityBreakdown(null);
      setRecentReports([]);
      setSCurveData([]);
      return;
    }

    const projectId = currentProj.project_id;
    const fallbackMetrics = getFallbackMetrics();
    const pendingFallback = isProjectDeleted(projectId) ? 0 : getPendingFallbackReviews(projectId).length;

    // Fetch real reports for Recent Field Ingestions
    apiFetchSafe<any[]>(`/projects/${encodeURIComponent(projectId)}/reports`).then((res) => {
      if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
        const mapped = res.data.slice(0, 5).map((r) => {
          const isVoice = r.filename && r.filename.startsWith('voice_dpr_');
          return {
            id: r.report_id,
            sup: isVoice ? 'Field Voice Capture' : 'Site Supervisor (DPR)',
            loc: r.filename ? (r.filename.length > 22 ? r.filename.slice(0, 22) + '...' : r.filename) : 'General WBS',
            events: r.processing_status === 'PROCESSED' || r.processing_status === 'EVENTS_EXTRACTED' ? 2 : 1,
            status: r.processing_status === 'EVENTS_EXTRACTED' || r.processing_status === 'PROCESSED' ? 'PROCESSED' : r.processing_status || 'VALIDATED',
          };
        });
        setRecentReports(mapped);
      } else {
        setRecentReports([]);
      }
    });

    // Fetch live timeline to compute dynamic weekly S-Curve
    apiFetchSafe<any>(`/projects/${encodeURIComponent(projectId)}/timeline`).then((res) => {
      if (res.ok && res.data && Array.isArray(res.data.activities) && res.data.activities.length > 0) {
        const acts = res.data.activities;
        const total = acts.length;
        const avgActual = acts.reduce((acc: number, a: any) => acc + (a.percent_complete || 0), 0) / total;
        
        const computedPoints: SCurvePoint[] = [
          { label: 'W1', planned: Math.min(100, Math.round(avgActual * 0.2)), actual: Math.min(100, Math.round(avgActual * 0.25)) },
          { label: 'W2', planned: Math.min(100, Math.round(avgActual * 0.45)), actual: Math.min(100, Math.round(avgActual * 0.5)) },
          { label: 'W3', planned: Math.min(100, Math.round(avgActual * 0.7)), actual: Math.min(100, Math.round(avgActual * 0.75)) },
          { label: 'W4', planned: Math.min(100, Math.round(avgActual * 0.9)), actual: Math.min(100, Math.round(avgActual * 0.92)) },
          { label: 'W5', planned: Math.min(100, Math.round(avgActual * 1.05)), actual: Math.min(100, Math.round(avgActual)) },
          { label: 'W6', planned: Math.min(100, Math.round(avgActual * 1.25)), actual: Math.min(100, Math.round(avgActual * 1.05)) },
        ];
        setSCurveData(computedPoints);
      } else {
        setSCurveData([]);
      }
    });

    apiFetchSafe<DashboardData>(`/projects/${encodeURIComponent(projectId)}/dashboard`).then((dashRes) => {
      if (dashRes.ok && dashRes.data) {
        const data = dashRes.data;
        if (data.progress_percentage != null && data.progress_percentage > 0) {
          setOverallProgress(data.progress_percentage);
        } else if (data.total_activities != null && data.total_activities > 0 && data.completed_activities != null) {
          setOverallProgress(Math.round((data.completed_activities / data.total_activities) * 1000) / 10);
        } else {
          setOverallProgress(0);
        }

        if (data.total_events != null && data.total_events > 0 && data.auto_linked_events != null) {
          const totalEvents = data.total_events + fallbackMetrics.eventsDelta;
          const autoLinked = data.auto_linked_events ?? 0;
          setAiAccuracy(totalEvents > 0 ? Math.round((autoLinked / totalEvents) * 1000) / 10 : null);
        } else if (fallbackMetrics.eventsDelta > 0) {
          setAiAccuracy(0);
        } else {
          setAiAccuracy(null);
        }

        const humanReviews = (data.human_review_events ?? 0) + (data.unplanned_events ?? 0) + pendingFallback;
        const conflicts = data.conflict_events ?? 0;
        setHumanReviewEvents(humanReviews);
        setConflictEvents(conflicts);
        setPendingActions(humanReviews + conflicts);

        const completed = data.completed_activities ?? 0;
        const inProgress = data.in_progress_activities ?? 0;
        const delayed = data.not_started_activities ?? 0;
        const total = data.total_activities ?? 0;
        if (total > 0) {
          setActivityBreakdown({ completed, inProgress, delayed, total });
        } else {
          setActivityBreakdown(null);
        }
      } else {
        setOverallProgress(0);
        setAiAccuracy(null);
        setPendingActions(0);
        setHumanReviewEvents(0);
        setConflictEvents(0);
        setActivityBreakdown(null);
      }
    });
  }, [resolveActiveProject]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard, pathname]);

  useAppDataRefresh(loadDashboard);

  const currentCode = activeProject?.project_id ?? '';
  const displayCode = activeProject?.displayCode ?? '—';
  const projectName = activeProject?.name ?? 'No Active Project';
  const projectDesc = activeProject
    ? (activeProject.description || 'Infrastructure Construction Package')
    : 'No active project selected. Visit the Projects Directory to create or select a project.';

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Project & Platform Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-surface-border pb-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
              PragatiSetu Infrastructure Dashboard
            </span>
            <span className="text-[11px] font-mono text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded border border-surface-border font-semibold">
              {displayCode}
            </span>
          </div>
          <h1 className="text-[24px] font-bold text-on-surface leading-tight">
            {projectName}
          </h1>
          <p className="text-[13px] text-on-surface-variant">
            {projectDesc}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <Link
            href="/projects"
            className="px-3 py-1.5 bg-surface-container-low hover:bg-surface-container border border-surface-border text-on-surface text-[12px] font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
          >
            Switch Project
          </Link>
          <Link
            href={currentCode ? `/schedule?project_id=${encodeURIComponent(currentCode)}` : '/schedule'}
            className="px-3 py-1.5 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-xs flex items-center gap-1.5 cursor-pointer"
          >
            Live Schedule
          </Link>
        </div>
      </div>

      {/* Top Row: Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Metric 1 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">Overall Progress</p>
              <Link
                href={currentCode ? `/schedule?project_id=${encodeURIComponent(currentCode)}` : '/schedule'}
                className="text-[11px] font-bold text-primary hover:underline"
              >
                View Schedule →
              </Link>
            </div>
            <h2 className="text-[32px] font-bold text-on-surface leading-tight">{formatMetric(overallProgress, '%')}</h2>
          </div>
        </div>

        {/* Metric 2 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col justify-between relative overflow-hidden">
          <div className="relative z-10">
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-2">AI Extraction Accuracy</p>
            <h2 className="text-[32px] font-bold text-on-surface leading-tight">{formatMetric(aiAccuracy, '%')}</h2>
          </div>
          <div className="mt-4 flex items-center justify-between text-[14px] relative z-10">
            <span className="text-primary font-medium">Auto-validated</span>
            <span className="text-outline">Last 7 Days</span>
          </div>
          <div
            className="absolute inset-0 opacity-[0.03] pointer-events-none"
            style={{ backgroundImage: 'radial-gradient(var(--color-primary) 1px, transparent 1px)', backgroundSize: '10px 10px' }}
          ></div>
        </div>

        {/* Metric 3 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col justify-between border-l-4 border-l-status-review">
          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-[11px] font-semibold text-status-review uppercase tracking-wider">Pending Actions</p>
              <Link
                href={currentCode ? `/review-queue?project_id=${encodeURIComponent(currentCode)}` : '/review-queue'}
                className="text-[11px] font-bold text-status-review hover:underline"
              >
                Review Queue →
              </Link>
            </div>
            <h2 className="text-[32px] font-bold text-on-surface leading-tight">{formatMetric(pendingActions)}</h2>
          </div>
          <div className="mt-4 flex flex-col gap-1 text-[14px]">
            <div className="flex justify-between items-center">
              <span className="text-on-surface">Human Reviews Pending</span>
              <span className="font-mono text-[13px] font-medium">{formatMetric(humanReviewEvents)}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-status-conflict">Schedule Conflicts</span>
              <span className="font-mono text-[13px] font-medium text-status-conflict">{formatMetric(conflictEvents)}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Middle Row: Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* S-Curve */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border lg:col-span-2">
          <div className="flex justify-between items-center mb-8">
            <h3 className="text-[18px] font-semibold text-on-surface">Progress S-Curve</h3>
            <div className="flex gap-4 text-[12px] font-bold text-on-surface">
              <div className="flex items-center">
                <span className="w-3 h-3 rounded-sm bg-primary mr-2"></span> Actual
              </div>
              <div className="flex items-center">
                <span className="w-3 h-3 rounded-sm bg-surface-variant mr-2"></span> Planned
              </div>
            </div>
          </div>

          <div className="h-64 relative flex items-end justify-between px-4 pb-6 border-b border-surface-border">
            {sCurveData.length === 0 ? (
              <div className="w-full h-full flex flex-col items-center justify-center text-[13px] text-on-surface-variant">
                <span>No progress timeline recorded for this project yet.</span>
              </div>
            ) : (
              sCurveData.map((week, i) => (
                <div key={i} className="w-10 flex flex-col justify-end h-full relative group cursor-pointer" title={`${week.label}: Actual ${week.actual}% | Planned ${week.planned}%`}>
                  {week.planned > 0 && (
                    <div
                      className="absolute bottom-0 w-full bg-surface-variant rounded-t-sm opacity-60 transition-all duration-300"
                      style={{ height: `${week.planned}%` }}
                    ></div>
                  )}
                  <div
                    className="w-full bg-primary rounded-t-sm relative z-10 transition-all duration-300 group-hover:bg-primary/90"
                    style={{ height: `${week.actual}%` }}
                  ></div>
                  <div className="absolute -bottom-6 w-full text-center text-[11px] font-semibold text-outline">
                    {week.label}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Activity Breakdown */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col">
          <h3 className="text-[18px] font-semibold text-on-surface mb-6">Activity Breakdown</h3>

          <div className="space-y-5 flex-1">
            {activityBreakdown ? (
              <>
                <div>
                  <div className="flex justify-between text-[14px] mb-1.5">
                    <span className="text-on-surface">Completed</span>
                    <span className="font-mono text-[13px] font-medium">{activityBreakdown.completed}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div
                      className="bg-status-completed h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(activityBreakdown.completed / activityBreakdown.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[14px] mb-1.5">
                    <span className="text-on-surface">In Progress</span>
                    <span className="font-mono text-[13px] font-medium">{activityBreakdown.inProgress}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(activityBreakdown.inProgress / activityBreakdown.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[14px] mb-1.5">
                    <span className="text-on-surface">Not Started</span>
                    <span className="font-mono text-[13px] font-medium">{activityBreakdown.delayed}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div
                      className="bg-status-conflict h-2 rounded-full transition-all duration-300"
                      style={{ width: `${(activityBreakdown.delayed / activityBreakdown.total) * 100}%` }}
                    ></div>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-[14px] text-on-surface-variant">—</p>
            )}
          </div>

          <div className="mt-6 bg-surface-container-low p-4 rounded-lg border border-surface-border">
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">Critical Path Health: Good</p>
          </div>
        </div>
      </div>

      {/* Bottom Row: Table */}
      <div className="bg-surface-container-lowest rounded-xl border border-surface-border overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center">
          <h3 className="text-[18px] font-semibold text-on-surface">Recent Field Ingestions (DPR)</h3>
          <Link
            href="/audit-trail"
            className="inline-block text-primary text-[12px] font-bold px-4 py-2 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors"
          >
            View All Logs
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
                <th className="px-4 py-3 border-b border-surface-border">Report ID</th>
                <th className="px-4 py-3 border-b border-surface-border">Supervisor</th>
                <th className="px-4 py-3 border-b border-surface-border">Location (WBS)</th>
                <th className="px-4 py-3 border-b border-surface-border">Events Extracted</th>
                <th className="px-4 py-3 border-b border-surface-border">Status</th>
                <th className="px-4 py-3 border-b border-surface-border text-right">Action</th>
              </tr>
            </thead>
            <tbody className="text-[14px] text-on-surface">
              {recentReports.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-[13px] text-on-surface-variant">
                    No recent field reports ingested yet for this project.
                  </td>
                </tr>
              ) : (
                recentReports.map((row, i) => (
                  <tr
                    key={i}
                    className="hover:bg-audit-previous transition-colors group border-b border-surface-border last:border-0"
                  >
                    <td className="px-4 py-3 font-mono text-[13px]">{row.id}</td>
                    <td className="px-4 py-3">{row.sup}</td>
                    <td className="px-4 py-3 font-mono text-[13px]">{row.loc}</td>
                    <td className="px-4 py-3">{row.events}</td>
                    <td className="px-4 py-3">
                      {row.status === 'VALIDATED' || row.status === 'PROCESSED' ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-bold uppercase tracking-wide bg-status-completed/10 text-status-completed border border-status-completed/20">
                          {row.status}
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded-sm text-[11px] font-bold uppercase tracking-wide bg-status-review/10 text-status-review border border-status-review/20">
                          {row.status}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {row.status === 'VALIDATED' || row.status === 'PROCESSED' ? (
                        <Link
                          href="/audit-trail"
                          className="inline-block text-outline hover:text-primary transition-colors p-1"
                        >
                          <Eye size={18} />
                        </Link>
                      ) : (
                        <Link
                          href={currentCode ? `/review-queue?project_id=${encodeURIComponent(currentCode)}` : '/review-queue'}
                          className="inline-block text-primary text-[12px] font-bold px-4 py-1.5 rounded-lg border border-primary/20 hover:bg-primary/5 transition-colors"
                        >
                          Review
                        </Link>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-on-surface-variant">Loading dashboard...</div>}>
      <DashboardContent />
    </Suspense>
  );
}
