'use client';


import { apiFetch, apiFetchSafe } from '@/lib/api';
import {
  Filter,
  ChevronDown,
  ChevronRight,
  Check,
  X,
  Download,
  Calendar,
  Layers,
  Activity as ActivityIcon,
  Clock,
  CheckCircle2,
  ExternalLink,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useState, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { useProjectContext } from '@/lib/project-context';
import { useAppDataRefresh } from '@/lib/app-sync';
import Link from 'next/link';

type GanttStyle = 'phase' | 'completed' | 'completed-thin' | 'in-progress' | 'not-started';

interface GanttBar {
  baselineLeft: number;
  baselineWidth: number;
  actualLeft: number;
  actualWidth: number;
  progressPercent: number;
  style: GanttStyle;
  hasConflict?: boolean;
}

interface TimelineActivity {
  activity_id: string;
  wbs_id: string;
  discipline?: string;
  description: string;
  planned_start: string;
  planned_finish: string;
  actual_start?: string | null;
  actual_finish?: string | null;
  percent_complete: number;
  status: string;
  predecessor_activity_id?: string | null;
}

interface TimelineResponse {
  project_id: string;
  project_name: string;
  total_activities: number;
  activities: TimelineActivity[];
}

interface ScheduleRow {
  wbsCode: string;
  name: string;
  percentComplete: number;
  statusLabel: 'Completed' | 'In Progress' | 'Not Started';
  level: 1 | 2 | 3;
  chevron: 'down' | 'right' | 'none';
  rowBg?: 'surface' | 'default';
  gantt: GanttBar;
  raw: TimelineActivity;
}

interface TimelinePeriod {
  label: string;
}

const FALLBACK_PERIODS: TimelinePeriod[] = [
  { label: 'Oct 01 - Oct 05' },
  { label: 'Oct 06 - Oct 10' },
  { label: 'Oct 11 - Oct 15' },
  { label: 'Oct 16 - Oct 20' },
];

function mapApiStatus(status: string): ScheduleRow['statusLabel'] {
  if (status === 'COMPLETED') return 'Completed';
  if (status === 'NOT_STARTED') return 'Not Started';
  return 'In Progress';
}

function mapGanttStyle(status: string, level: 1 | 2 | 3): GanttStyle {
  if (status === 'COMPLETED') return level >= 3 ? 'completed-thin' : 'completed';
  if (status === 'NOT_STARTED') return 'not-started';
  return 'in-progress';
}

function formatShortDate(d: Date): string {
  return d.toLocaleDateString('en-US', { month: 'short', day: '2-digit' });
}

function generatePeriods(minDate: Date, maxDate: Date): TimelinePeriod[] {
  const periods: TimelinePeriod[] = [];
  const current = new Date(minDate);
  for (let i = 0; i < 4; i++) {
    const end = new Date(current);
    end.setDate(end.getDate() + 4);
    periods.push({ label: `${formatShortDate(current)} - ${formatShortDate(end)}` });
    current.setDate(current.getDate() + 5);
    if (current > maxDate) break;
  }
  return periods.length > 0 ? periods : FALLBACK_PERIODS;
}

function getTodayLeft(minDate: Date, maxDate: Date): number {
  const today = new Date();
  const rangeMs = maxDate.getTime() - minDate.getTime() || 86400000;
  const chartWidth = 760;
  const leftPad = 40;
  const clamped = Math.min(Math.max(today.getTime(), minDate.getTime()), maxDate.getTime());
  return leftPad + ((clamped - minDate.getTime()) / rangeMs) * chartWidth;
}

function mapApiToRows(data: TimelineResponse): { rows: ScheduleRow[]; periods: TimelinePeriod[]; todayLeft: number } | null {
  const activities = data.activities;
  if (!activities?.length) return null;

  const allDates = activities.flatMap((a) =>
    [a.planned_start, a.planned_finish, a.actual_start, a.actual_finish].filter(Boolean) as string[]
  );
  const minDate = new Date(Math.min(...allDates.map((d) => new Date(d).getTime())));
  const maxDate = new Date(Math.max(...allDates.map((d) => new Date(d).getTime())));
  const rangeMs = maxDate.getTime() - minDate.getTime() || 86400000;
  const chartWidth = 760;
  const leftPad = 40;

  const toLeft = (dateStr: string) =>
    leftPad + ((new Date(dateStr).getTime() - minDate.getTime()) / rangeMs) * chartWidth;

  const rows: ScheduleRow[] = activities.map((act) => {
    const baselineLeft = toLeft(act.planned_start);
    const baselineWidth = Math.max(toLeft(act.planned_finish) - baselineLeft, 40);
    const actualStart = act.actual_start || act.planned_start;
    const actualFinish = act.actual_finish || act.planned_finish;
    const actualLeft = toLeft(actualStart);
    const actualWidth = Math.max(toLeft(actualFinish) - actualLeft, 20);
    const depth = act.wbs_id ? act.wbs_id.split('/').length : 1;
    const level: 1 | 2 | 3 = depth <= 1 ? 1 : depth === 2 ? 2 : 3;
    const chevron: ScheduleRow['chevron'] = level < 3 ? 'right' : 'none';

    return {
      wbsCode: act.activity_id,
      name: act.description,
      percentComplete: act.percent_complete,
      statusLabel: mapApiStatus(act.status),
      level,
      chevron,
      rowBg: level === 1 ? 'surface' : 'default',
      gantt: {
        baselineLeft,
        baselineWidth,
        actualLeft,
        actualWidth,
        progressPercent: act.percent_complete,
        style: mapGanttStyle(act.status, level),
        hasConflict: act.status === 'IN_PROGRESS' && act.percent_complete < 50,
      },
      raw: act,
    };
  });

  return {
    rows,
    periods: generatePeriods(minDate, maxDate),
    todayLeft: getTodayLeft(minDate, maxDate),
  };
}

function statusBadgeClass(statusLabel: ScheduleRow['statusLabel']) {
  if (statusLabel === 'Completed') {
    return 'px-2 py-0.5 rounded-sm text-[10px] font-bold bg-status-completed/10 text-status-completed border border-status-completed/20 uppercase tracking-wide';
  }
  if (statusLabel === 'In Progress') {
    return 'px-2 py-0.5 rounded-sm text-[10px] font-bold bg-primary/10 text-primary border border-primary/20 uppercase tracking-wide';
  }
  return 'px-2 py-0.5 rounded-sm text-[10px] font-bold bg-surface-container-high text-on-surface-variant border border-surface-border uppercase tracking-wide';
}

function ScheduleContent() {
  const searchParams = useSearchParams();
  const { selectedProjectId: projectId, projects } = useProjectContext();
  const currentProject = projects.find(p => p.project_id === projectId);

  const [rows, setRows] = useState<ScheduleRow[]>([]);
  const [periods, setPeriods] = useState<TimelinePeriod[]>(FALLBACK_PERIODS);
  const [todayLeft, setTodayLeft] = useState(280);
  const [timeScale, setTimeScale] = useState<'days' | 'weeks' | 'months'>('days');
  const [statusFilter, setStatusFilter] = useState<'all' | 'in-progress' | 'completed' | 'delayed'>('all');
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [selectedActivity, setSelectedActivity] = useState<TimelineActivity | null>(null);
  const [exportNotice, setExportNotice] = useState(false);

  const urlSearch = searchParams.get('search') ?? '';
  const [searchQuery, setSearchQuery] = useState(urlSearch);

  useEffect(() => {
    setSearchQuery(urlSearch);
  }, [urlSearch]);

  const loadTimeline = useCallback(() => {
    if (!projectId) return;
    apiFetch<TimelineResponse>(`/projects/${projectId}/timeline`)
      .then((data) => {
        const mapped = mapApiToRows(data);
        if (mapped) {
          setRows(mapped.rows);
          setPeriods(mapped.periods);
          setTodayLeft(mapped.todayLeft);
        }
      })
      .catch(() => {
        // fetch fallback if offline
        apiFetchSafe<any[]>(`/projects/${projectId}/activities`).then((res) => {
          if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
            const mapped = mapApiToRows({
              project_id: projectId || '',
              project_name: currentProject?.name || projectId || '',
              total_activities: res.data.length,
              activities: res.data,
            });
            if (mapped) {
              setRows(mapped.rows);
              setPeriods(mapped.periods);
              setTodayLeft(mapped.todayLeft);
            }
          }
        });
      });
  }, [projectId, currentProject]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  useAppDataRefresh(loadTimeline);

  // Compute displayed periods based on timescale
  const displayPeriods =
    timeScale === 'weeks'
      ? [
          { label: 'W35 · Aug 24 - Aug 30' },
          { label: 'W36 · Aug 31 - Sep 06' },
          { label: 'W37 · Sep 07 - Sep 13' },
          { label: 'W38 · Sep 14 - Sep 20' },
        ]
      : timeScale === 'months'
      ? [
          { label: 'August 2026' },
          { label: 'September 2026' },
          { label: 'October 2026' },
          { label: 'November 2026' },
        ]
      : periods;

  // Filter rows
  const filteredRows = rows.filter((row) => {
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const match =
        row.wbsCode.toLowerCase().includes(q) ||
        row.name.toLowerCase().includes(q) ||
        (row.raw.discipline && row.raw.discipline.toLowerCase().includes(q));
      if (!match) return false;
    }
    if (statusFilter === 'in-progress') return row.statusLabel === 'In Progress';
    if (statusFilter === 'completed') return row.statusLabel === 'Completed';
    if (statusFilter === 'delayed') return Boolean(row.gantt.hasConflict);
    return true;
  });

  const handleExportCSV = () => {
    const headers = ['Activity ID', 'Description', 'Discipline', 'WBS Node', 'Planned Start', 'Planned Finish', 'Actual Start', 'Actual Finish', 'Progress %', 'Status'];
    const dataRows = filteredRows.map((r) => [
      r.raw.activity_id,
      `"${r.raw.description}"`,
      `"${r.raw.discipline || 'General'}"`,
      `"${r.raw.wbs_id}"`,
      r.raw.planned_start,
      r.raw.planned_finish,
      r.raw.actual_start || 'N/A',
      r.raw.actual_finish || 'N/A',
      `${r.raw.percent_complete}%`,
      r.raw.status,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...dataRows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `pragatisetu-${projectId}-schedule-${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    setExportNotice(true);
    setTimeout(() => setExportNotice(false), 3000);
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-surface-bright w-full overflow-hidden">
      {/* Toolbar */}
      <div className="px-6 py-3 border-b border-surface-border bg-surface-container-lowest flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          {/* Active Search Query Badge */}
          {searchQuery && (
            <span className="flex items-center gap-1.5 px-3 py-1 bg-primary/10 text-primary border border-primary/20 rounded-lg text-[12px] font-semibold">
              Filter: &quot;{searchQuery}&quot;
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                className="hover:text-status-conflict transition-colors cursor-pointer"
                title="Clear filter"
              >
                <X size={13} />
              </button>
            </span>
          )}

          {/* Filter Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setIsFilterOpen(!isFilterOpen)}
              className={`px-3 py-1.5 border rounded-lg text-[13px] font-medium flex items-center gap-2 transition-colors cursor-pointer ${
                statusFilter !== 'all'
                  ? 'bg-primary/10 border-primary text-primary font-bold'
                  : 'bg-surface-container-lowest hover:bg-surface-container-low border-surface-border text-on-surface'
              }`}
            >
              <Filter size={16} />
              <span>
                {statusFilter === 'all' && 'Filter'}
                {statusFilter === 'in-progress' && 'In Progress'}
                {statusFilter === 'completed' && 'Completed'}
                {statusFilter === 'delayed' && 'Delayed'}
              </span>
              {statusFilter !== 'all' && (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    setStatusFilter('all');
                  }}
                  className="hover:text-status-conflict p-0.5"
                >
                  <X size={13} />
                </span>
              )}
            </button>

            {isFilterOpen && (
              <div className="absolute left-0 mt-2 w-48 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-30 p-1.5 space-y-0.5 animate-fadeIn">
                {[
                  { id: 'all', label: 'All Activities' },
                  { id: 'in-progress', label: 'In Progress Only' },
                  { id: 'completed', label: 'Completed Only' },
                  { id: 'delayed', label: 'Delayed / Conflicts' },
                ].map((f) => (
                  <button
                    key={f.id}
                    type="button"
                    onClick={() => {
                      setStatusFilter(f.id as typeof statusFilter);
                      setIsFilterOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 rounded-lg text-[12px] flex items-center justify-between transition-colors cursor-pointer ${
                      statusFilter === f.id
                        ? 'bg-primary/10 text-primary font-bold'
                        : 'text-on-surface hover:bg-surface-container-low'
                    }`}
                  >
                    <span>{f.label}</span>
                    {statusFilter === f.id && <Check size={14} className="text-primary" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="h-6 w-px bg-surface-border mx-1"></div>

          {/* Timescale Selector */}
          <div className="flex items-center bg-surface-container-low rounded-lg border border-surface-border p-0.5">
            <button
              type="button"
              onClick={() => setTimeScale('days')}
              className={`px-4 py-1.5 rounded-sm text-[13px] font-medium transition-all cursor-pointer ${
                timeScale === 'days'
                  ? 'bg-surface-container-lowest text-on-surface shadow-sm font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Days
            </button>
            <button
              type="button"
              onClick={() => setTimeScale('weeks')}
              className={`px-4 py-1.5 rounded-sm text-[13px] font-medium transition-all cursor-pointer ${
                timeScale === 'weeks'
                  ? 'bg-surface-container-lowest text-on-surface shadow-sm font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Weeks
            </button>
            <button
              type="button"
              onClick={() => setTimeScale('months')}
              className={`px-4 py-1.5 rounded-sm text-[13px] font-medium transition-all cursor-pointer ${
                timeScale === 'months'
                  ? 'bg-surface-container-lowest text-on-surface shadow-sm font-semibold'
                  : 'text-on-surface-variant hover:text-on-surface'
              }`}
            >
              Months
            </button>
          </div>

          {/* Export CSV */}
          <button
            type="button"
            onClick={handleExportCSV}
            className="px-3 py-1.5 bg-surface-container-low hover:bg-surface-container border border-surface-border text-on-surface text-[12px] font-bold rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer ml-1"
            title="Export WBS Schedule to CSV"
          >
            <Download size={14} />
            <span className="hidden sm:inline">Export CSV</span>
          </button>
        </div>

        <div className="flex items-center gap-4">
          <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-1 bg-surface-container-low border border-surface-border rounded text-[11px] font-bold text-on-surface">
            {currentProject ? `${currentProject.name} (${projectId})` : (projectId || 'No Project')}
          </span>
          <div className="flex items-center gap-5 text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
            <div className="flex items-center gap-2">
              <div className="w-4 h-1 bg-surface-border rounded-full"></div> Baseline
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 bg-primary rounded-sm"></div> Actual
            </div>
          </div>
        </div>
      </div>

      {exportNotice && (
        <div className="bg-emerald-500/10 border-b border-emerald-500/20 px-6 py-2 text-[12px] font-bold text-emerald-600 flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 size={15} />
          <span>WBS Schedule exported successfully to CSV.</span>
        </div>
      )}

      {/* Split View */}
      <div className="flex-1 flex overflow-hidden bg-surface">
        {/* Left: WBS Table */}
        <div className="w-[42%] flex flex-col border-r border-surface-border bg-surface-container-lowest shrink-0 z-10 shadow-[2px_0_8px_rgba(0,0,0,0.02)]">
          {/* Header */}
          <div className="flex border-b border-surface-border bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider sticky top-0 z-20">
            <div className="px-4 py-3 w-32 shrink-0 border-r border-surface-border">WBS Code</div>
            <div className="px-4 py-3 flex-1 border-r border-surface-border">Activity Name</div>
            <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border">% Comp</div>
            <div className="px-4 py-3 w-32 shrink-0">Status</div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto">
            {filteredRows.length > 0 ? (
              filteredRows.map((row, index) => {
                const wbsPadding = row.level === 3 ? 'pl-12' : row.level === 2 ? 'pl-8' : '';
                const isVariant = row.level === 3 || (row.statusLabel === 'Not Started' && row.percentComplete === 0);

                return (
                  <div
                    key={`${row.wbsCode}-${index}`}
                    onClick={() => setSelectedActivity(row.raw)}
                    className={cn(
                      'flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer',
                      row.rowBg === 'surface' ? 'bg-surface' : 'bg-surface-container-lowest'
                    )}
                    title="Click to view activity details"
                  >
                    <div
                      className={cn(
                        'px-4 py-3 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] flex items-center gap-1',
                        wbsPadding,
                        row.level === 1 ? 'font-bold text-on-surface' : isVariant ? 'text-on-surface-variant' : 'text-on-surface'
                      )}
                    >
                      {row.chevron === 'down' && <ChevronDown size={16} className="text-outline" />}
                      {row.chevron === 'right' && <ChevronRight size={16} className="text-outline" />}
                      {row.chevron === 'none' && <span className="w-4"></span>}
                      {row.wbsCode}
                    </div>
                    <div
                      className={cn(
                        'px-4 py-3 flex-1 border-r border-surface-border text-[14px] truncate group-hover:text-primary transition-colors',
                        row.level === 1 ? 'text-on-surface font-semibold' : isVariant ? 'text-on-surface-variant' : 'text-on-surface'
                      )}
                    >
                      {row.name}
                    </div>
                    <div
                      className={cn(
                        'px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px] font-semibold',
                        isVariant ? 'text-on-surface-variant' : 'text-on-surface'
                      )}
                    >
                      {row.percentComplete}%
                    </div>
                    <div className="px-4 py-3 w-32 shrink-0 flex items-center">
                      <span className={statusBadgeClass(row.statusLabel)}>{row.statusLabel}</span>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="p-8 text-center text-on-surface-variant text-[13px]">
                No activities match your filter.
              </div>
            )}
          </div>
        </div>

        {/* Right: Gantt Chart */}
        <div className="flex-1 overflow-x-auto overflow-y-hidden bg-surface-bright relative">
          {/* Grid Background */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              backgroundSize: '40px 100%',
              backgroundImage: 'linear-gradient(to right, var(--color-surface-border) 1px, transparent 1px)',
            }}
          ></div>

          {/* Timeline Header */}
          <div className="flex border-b border-surface-border bg-surface-container-lowest text-[11px] font-semibold text-on-surface-variant sticky top-0 z-20 min-w-max h-[45px]">
            <div className="absolute inset-0 flex items-end pb-2 px-1">
              {displayPeriods.map((period, i) => (
                <div key={i} className="w-[200px] shrink-0 border-l border-surface-border pl-2">
                  {period.label}
                </div>
              ))}
            </div>
          </div>

          {/* Timeline Body Rows */}
          <div className="min-w-max relative" style={{ minHeight: 'calc(100% - 45px)' }}>
            {filteredRows.map((row, index) => {
              const { gantt } = row;
              return (
                <div
                  key={`gantt-${row.wbsCode}-${index}`}
                  onClick={() => setSelectedActivity(row.raw)}
                  className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50 cursor-pointer"
                  title="Click to view activity dossier"
                >
                  {/* Baseline Bar */}
                  <div
                    className="absolute top-[10px] h-[4px] bg-surface-border rounded-full"
                    style={{ left: `${gantt.baselineLeft}px`, width: `${gantt.baselineWidth}px` }}
                  ></div>

                  {/* Actual Progress Bar */}
                  {gantt.style === 'completed' && (
                    <div
                      className="absolute top-[18px] h-[14px] bg-status-completed rounded-sm"
                      style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
                    ></div>
                  )}

                  {gantt.style === 'completed-thin' && (
                    <div
                      className="absolute top-[22px] h-[6px] bg-status-completed rounded-xs"
                      style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
                    ></div>
                  )}

                  {gantt.style === 'in-progress' && (
                    <div
                      className="absolute top-[18px] h-[14px] bg-primary rounded-sm overflow-hidden"
                      style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
                    >
                      <div
                        className="h-full bg-primary-fixed"
                        style={{ width: `${gantt.progressPercent}%` }}
                      ></div>
                    </div>
                  )}

                  {gantt.style === 'phase' && (
                    <div
                      className="absolute top-[18px] h-[14px] bg-surface-container-high rounded-sm border border-surface-border overflow-hidden"
                      style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
                    >
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${gantt.progressPercent}%` }}
                      ></div>
                    </div>
                  )}

                  {gantt.hasConflict && (
                    <div
                      className="absolute top-[14px] h-[22px] border-2 border-dashed border-status-conflict rounded-sm pointer-events-none"
                      style={{ left: `${gantt.actualLeft - 2}px`, width: `${gantt.actualWidth + 4}px` }}
                    ></div>
                  )}
                </div>
              );
            })}

            {/* Today Marker */}
            <div
              className="absolute top-0 bottom-0 w-[2px] bg-status-review/50 border-l border-dashed border-status-review z-10"
              style={{ left: `${todayLeft}px` }}
            >
              <div className="absolute -top-5 -left-6 bg-status-review text-on-error font-semibold text-[10px] px-2 py-0.5 rounded tracking-wider">
                TODAY
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Activity Dossier Modal */}
      {selectedActivity && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-surface-container-lowest border border-surface-border rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5">
            <div className="flex items-start justify-between border-b border-surface-border pb-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-[12px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20">
                    {selectedActivity.activity_id}
                  </span>
                  <span className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant bg-surface-container px-2 py-0.5 rounded">
                    {selectedActivity.discipline || 'General'}
                  </span>
                </div>
                <h3 className="text-[17px] font-bold text-on-surface leading-tight">
                  {selectedActivity.description}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedActivity(null)}
                className="p-1 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-[13px]">
              <div className="p-3 bg-surface-container-low rounded-xl border border-surface-border">
                <span className="text-[11px] text-on-surface-variant block uppercase font-semibold mb-1">WBS Hierarchy</span>
                <span className="font-mono text-on-surface font-medium break-all">{selectedActivity.wbs_id}</span>
              </div>
              <div className="p-3 bg-surface-container-low rounded-xl border border-surface-border">
                <span className="text-[11px] text-on-surface-variant block uppercase font-semibold mb-1">Status</span>
                <span className="font-bold text-primary">{selectedActivity.status}</span>
              </div>
              <div className="p-3 bg-surface-container-low rounded-xl border border-surface-border">
                <span className="text-[11px] text-on-surface-variant block uppercase font-semibold mb-1">Planned Timeline</span>
                <span className="font-mono text-on-surface">{selectedActivity.planned_start} → {selectedActivity.planned_finish}</span>
              </div>
              <div className="p-3 bg-surface-container-low rounded-xl border border-surface-border">
                <span className="text-[11px] text-on-surface-variant block uppercase font-semibold mb-1">Actual Timeline</span>
                <span className="font-mono text-on-surface">{selectedActivity.actual_start || 'Pending'} → {selectedActivity.actual_finish || 'In progress'}</span>
              </div>
            </div>

            {/* Progress Gauge */}
            <div className="p-3.5 bg-surface-container-low rounded-xl border border-surface-border">
              <div className="flex justify-between items-center text-[13px] font-bold mb-2">
                <span className="text-on-surface">Physical Progress Actuals</span>
                <span className="text-primary font-mono">{selectedActivity.percent_complete}%</span>
              </div>
              <div className="w-full bg-surface-container rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-primary h-full transition-all duration-300 rounded-full"
                  style={{ width: `${selectedActivity.percent_complete}%` }}
                ></div>
              </div>
            </div>

            <div className="flex items-center justify-between pt-2 border-t border-surface-border">
              <Link
                href={`/reports?activity=${encodeURIComponent(selectedActivity.activity_id)}`}
                onClick={() => setSelectedActivity(null)}
                className="text-[12px] font-bold text-primary hover:underline flex items-center gap-1"
              >
                <span>Upload Field DPR for this activity</span>
                <ExternalLink size={13} />
              </Link>
              <button
                type="button"
                onClick={() => setSelectedActivity(null)}
                className="px-4 py-2 bg-surface-container hover:bg-surface-container-high text-on-surface text-[12px] font-bold rounded-lg transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Schedule() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-on-surface-variant">Loading schedule...</div>}>
      <ScheduleContent />
    </Suspense>
  );
}
