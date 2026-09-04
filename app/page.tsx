'use client';

import { apiFetch } from '@/lib/api';
import { useAppDataRefresh } from '@/lib/app-sync';
import { getFallbackMetrics, getPendingFallbackReviews } from '@/lib/report-fallback';
import { Eye } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

type DashboardData = {
  total_activities?: number;
  completed_activities?: number;
  in_progress_activities?: number;
  not_started_activities?: number;
  total_events?: number;
  auto_linked_events?: number;
  human_review_events?: number;
  conflict_events?: number;
};

const DEMO_S_CURVE = [
  { actual: 10, planned: 0, label: 'W1' },
  { actual: 25, planned: 0, label: 'W2' },
  { actual: 40, planned: 45, label: 'W3' },
  { actual: 55, planned: 60, label: 'W4' },
  { actual: 68, planned: 75, label: 'W5' },
  { actual: 85, planned: 90, label: 'W6' },
  { actual: 92, planned: 100, label: 'W7' },
];

const DEMO_DPR_ROWS = [
  { id: 'RPT-8832', sup: 'J. Miller', loc: 'L5-A-North', events: 14, status: 'VALIDATED' },
  { id: 'RPT-8831', sup: 'S. Gupta', loc: 'L5-B-South', events: 8, status: 'REVIEW REQUIRED' },
  { id: 'RPT-8830', sup: 'A. Chen', loc: 'L6-Foundation', events: 22, status: 'VALIDATED' },
];

function formatMetric(value: number | null, suffix = '') {
  return value == null ? '—' : `${value}${suffix}`;
}

export default function Dashboard() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const projectId = searchParams.get('project_id') ?? 'PROJ-ALPHA';

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

  const loadDashboard = useCallback(() => {
    const fallbackMetrics = getFallbackMetrics();
    const pendingFallback = getPendingFallbackReviews().length;

    apiFetch<DashboardData>(`/projects/${projectId}/dashboard`)
      .then((data) => {
        if (data.total_activities != null && data.total_activities > 0 && data.completed_activities != null) {
          setOverallProgress(Math.round((data.completed_activities / data.total_activities) * 1000) / 10);
        } else {
          setOverallProgress(null);
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

        const humanReviews = (data.human_review_events ?? 0) + pendingFallback;
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
      })
      .catch(() => {
        const pendingFallbackOnly = getPendingFallbackReviews().length;
        if (pendingFallbackOnly > 0) {
          setHumanReviewEvents(pendingFallbackOnly);
          setPendingActions(pendingFallbackOnly);
        } else {
          setOverallProgress(null);
          setAiAccuracy(null);
          setPendingActions(null);
          setHumanReviewEvents(null);
          setConflictEvents(null);
          setActivityBreakdown(null);
        }
      });
  }, [projectId]);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard, pathname]);

  useAppDataRefresh(loadDashboard);

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      
      {/* Top Row: Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        
        {/* Metric 1 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col justify-between">
          <div>
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-2">Overall Progress</p>
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
          <div className="absolute inset-0 opacity-[0.03] pointer-events-none" style={{ backgroundImage: 'radial-gradient(var(--color-primary) 1px, transparent 1px)', backgroundSize: '10px 10px' }}></div>
        </div>

        {/* Metric 3 */}
        <div className="bg-surface-container-lowest p-6 rounded-xl border border-surface-border flex flex-col justify-between border-l-4 border-l-status-review">
          <div>
            <p className="text-[11px] font-semibold text-status-review uppercase tracking-wider mb-2">Pending Actions</p>
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
              <div className="flex items-center"><span className="w-3 h-3 rounded-sm bg-primary mr-2"></span> Actual</div>
              <div className="flex items-center"><span className="w-3 h-3 rounded-sm bg-surface-variant mr-2"></span> Planned</div>
            </div>
          </div>
          
          <div className="h-64 relative flex items-end justify-between px-4 pb-6 border-b border-surface-border">
            {/* Bars simulation */}
            {DEMO_S_CURVE.map((week, i) => (
              <div key={i} className="w-10 flex flex-col justify-end h-full relative group">
                {week.planned > 0 && (
                  <div 
                    className="absolute bottom-0 w-full bg-surface-variant rounded-t-sm opacity-60" 
                    style={{ height: `${week.planned}%` }}
                  ></div>
                )}
                <div 
                  className="w-full bg-primary rounded-t-sm relative z-10 transition-all group-hover:bg-primary/90" 
                  style={{ height: `${week.actual}%` }}
                ></div>
                <div className="absolute -bottom-6 w-full text-center text-[11px] font-semibold text-outline">{week.label}</div>
              </div>
            ))}
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
                    <div className="bg-status-completed h-2 rounded-full" style={{ width: `${(activityBreakdown.completed / activityBreakdown.total) * 100}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[14px] mb-1.5">
                    <span className="text-on-surface">In Progress</span>
                    <span className="font-mono text-[13px] font-medium">{activityBreakdown.inProgress}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div className="bg-primary h-2 rounded-full" style={{ width: `${(activityBreakdown.inProgress / activityBreakdown.total) * 100}%` }}></div>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between text-[14px] mb-1.5">
                    <span className="text-on-surface">Not Started</span>
                    <span className="font-mono text-[13px] font-medium">{activityBreakdown.delayed}</span>
                  </div>
                  <div className="w-full bg-surface-variant rounded-full h-2">
                    <div className="bg-status-conflict h-2 rounded-full" style={{ width: `${(activityBreakdown.delayed / activityBreakdown.total) * 100}%` }}></div>
                  </div>
                </div>
              </>
            ) : (
              <p className="text-[14px] text-on-surface-variant">—</p>
            )}
          </div>

          <div className="mt-6 bg-surface-container-low p-4 rounded-lg border border-surface-border">
            <p className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">Critical Path Health</p>
          </div>
        </div>

      </div>

      {/* Bottom Row: Table */}
      <div className="bg-surface-container-lowest rounded-xl border border-surface-border overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center">
          <h3 className="text-[18px] font-semibold text-on-surface">Recent Field Ingestions (DPR)</h3>
          <Link href="/audit-trail" className="inline-block text-primary text-[12px] font-bold px-4 py-2 rounded-lg border border-outline-variant hover:bg-surface-container-low transition-colors">
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
              {DEMO_DPR_ROWS.map((row, i) => (
                <tr key={i} className="hover:bg-audit-previous transition-colors group border-b border-surface-border last:border-0">
                  <td className="px-4 py-3 font-mono text-[13px]">{row.id}</td>
                  <td className="px-4 py-3">{row.sup}</td>
                  <td className="px-4 py-3 font-mono text-[13px]">{row.loc}</td>
                  <td className="px-4 py-3">{row.events}</td>
                  <td className="px-4 py-3">
                    {row.status === 'VALIDATED' ? (
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
                    {row.status === 'VALIDATED' ? (
                      <Link href="/audit-trail" className="inline-block text-outline hover:text-primary transition-colors p-1">
                        <Eye size={18} />
                      </Link>
                    ) : (
                      <Link href="/review-queue" className="inline-block text-primary text-[12px] font-bold px-4 py-1.5 rounded-lg border border-primary/20 hover:bg-primary/5 transition-colors">
                        Review
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
