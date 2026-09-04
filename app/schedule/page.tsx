'use client';

import { apiFetch } from '@/lib/api';
import { Filter, ChevronDown, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useEffect, useState } from 'react';

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
  description: string;
  planned_start: string;
  planned_finish: string;
  actual_start?: string | null;
  actual_finish?: string | null;
  percent_complete: number;
  status: string;
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
}

interface TimelinePeriod {
  label: string;
}

const FALLBACK_ROWS: ScheduleRow[] = [
  {
    wbsCode: 'A.1',
    name: 'Site Preparation Phase',
    percentComplete: 45,
    statusLabel: 'In Progress',
    level: 1,
    chevron: 'down',
    rowBg: 'surface',
    gantt: { baselineLeft: 40, baselineWidth: 600, actualLeft: 40, actualWidth: 620, progressPercent: 45, style: 'phase' },
  },
  {
    wbsCode: 'A.1.1',
    name: 'Survey & Mapping',
    percentComplete: 100,
    statusLabel: 'Completed',
    level: 2,
    chevron: 'down',
    gantt: { baselineLeft: 40, baselineWidth: 160, actualLeft: 40, actualWidth: 160, progressPercent: 100, style: 'completed' },
  },
  {
    wbsCode: '24P201',
    name: 'Topographical Survey',
    percentComplete: 100,
    statusLabel: 'Completed',
    level: 3,
    chevron: 'none',
    gantt: { baselineLeft: 40, baselineWidth: 160, actualLeft: 40, actualWidth: 160, progressPercent: 100, style: 'completed-thin' },
  },
  {
    wbsCode: 'A.1.2',
    name: 'Clearance & Grading',
    percentComplete: 20,
    statusLabel: 'In Progress',
    level: 2,
    chevron: 'right',
    gantt: { baselineLeft: 200, baselineWidth: 240, actualLeft: 240, actualWidth: 280, progressPercent: 20, style: 'in-progress', hasConflict: true },
  },
  {
    wbsCode: 'A.1.3',
    name: 'Foundation Excavation',
    percentComplete: 0,
    statusLabel: 'Not Started',
    level: 2,
    chevron: 'right',
    gantt: { baselineLeft: 440, baselineWidth: 200, actualLeft: 520, actualWidth: 200, progressPercent: 0, style: 'not-started' },
  },
];

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
    const depth = act.wbs_id.split('.').length;
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
      },
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
    return 'px-2 py-0.5 rounded-sm text-[10px] font-bold bg-primary-fixed/50 text-primary border border-primary-fixed uppercase tracking-wide';
  }
  return 'px-2 py-0.5 rounded-sm text-[10px] font-bold bg-surface-container-high text-on-surface-variant border border-surface-border uppercase tracking-wide';
}

function renderTableRow(row: ScheduleRow, index: number) {
  const wbsPadding = row.level === 3 ? 'pl-12' : row.level === 2 ? 'pl-8' : '';
  const isVariant = row.level === 3 || (row.statusLabel === 'Not Started' && row.percentComplete === 0);

  return (
    <div
      key={`${row.wbsCode}-${index}`}
      className={cn(
        'flex border-b border-surface-border hover:bg-surface-container transition-colors group cursor-pointer',
        row.rowBg === 'surface' ? 'bg-surface' : 'bg-surface-container-lowest'
      )}
    >
      <div className={cn('px-4 py-3 w-32 shrink-0 border-r border-surface-border font-mono text-[13px] flex items-center gap-1', wbsPadding, row.level === 1 ? 'font-bold text-on-surface' : isVariant ? 'text-on-surface-variant' : 'text-on-surface')}>
        {row.chevron === 'down' && <ChevronDown size={16} className="text-outline" />}
        {row.chevron === 'right' && <ChevronRight size={16} className="text-outline" />}
        {row.chevron === 'none' && <span className="w-4"></span>}
        {' '}{row.wbsCode}
      </div>
      <div className={cn('px-4 py-3 flex-1 border-r border-surface-border text-[14px] truncate', row.level === 1 ? 'text-on-surface font-semibold' : isVariant ? 'text-on-surface-variant' : 'text-on-surface')}>
        {row.name}
      </div>
      <div className={cn('px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border font-mono text-[13px]', isVariant ? 'text-on-surface-variant' : 'text-on-surface')}>
        {row.percentComplete}%
      </div>
      <div className="px-4 py-3 w-32 shrink-0 flex items-center">
        <span className={statusBadgeClass(row.statusLabel)}>{row.statusLabel}</span>
      </div>
    </div>
  );
}

function renderGanttRow(row: ScheduleRow, index: number) {
  const { gantt } = row;

  return (
    <div key={`gantt-${row.wbsCode}-${index}`} className="h-[45px] border-b border-surface-border relative group hover:bg-surface-container-low/50">
      <div
        className="absolute top-[10px] h-[4px] bg-surface-border rounded-full"
        style={{ left: `${gantt.baselineLeft}px`, width: `${gantt.baselineWidth}px` }}
      ></div>

      {gantt.style === 'phase' && (
        <>
          <div
            className="absolute top-[20px] h-[12px] bg-secondary rounded-sm shadow-sm flex items-center px-1 overflow-hidden"
            style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
          >
            <div className="h-full bg-primary/20" style={{ width: `${gantt.progressPercent}%` }}></div>
          </div>
        </>
      )}

      {gantt.style === 'completed' && (
        <div
          className="absolute top-[22px] h-[8px] bg-status-completed rounded-sm shadow-sm"
          style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
        ></div>
      )}

      {gantt.style === 'completed-thin' && (
        <div
          className="absolute top-[24px] h-[4px] bg-status-completed rounded-full"
          style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
        ></div>
      )}

      {gantt.style === 'in-progress' && (
        <>
          <div
            className="absolute top-[22px] h-[8px] bg-primary rounded-sm shadow-sm flex overflow-hidden"
            style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
          >
            <div className="h-full bg-primary-fixed" style={{ width: `${gantt.progressPercent}%` }}></div>
          </div>
          {gantt.hasConflict && (
            <div
              className="absolute top-[18px] w-4 h-4 rounded-full bg-status-conflict border-2 border-surface-container-lowest flex items-center justify-center z-10"
              style={{ left: `${gantt.actualLeft + gantt.actualWidth * 0.97}px` }}
            ></div>
          )}
        </>
      )}

      {gantt.style === 'not-started' && (
        <div
          className="absolute top-[22px] h-[8px] border border-outline border-dashed rounded-sm"
          style={{ left: `${gantt.actualLeft}px`, width: `${gantt.actualWidth}px` }}
        ></div>
      )}
    </div>
  );
}

export default function Schedule() {
  const [rows, setRows] = useState<ScheduleRow[]>(FALLBACK_ROWS);
  const [periods, setPeriods] = useState<TimelinePeriod[]>(FALLBACK_PERIODS);
  const [todayLeft, setTodayLeft] = useState(280);

  useEffect(() => {
    apiFetch<TimelineResponse>(`/projects/PROJ-ALPHA/timeline`)
      .then((data) => {
        const mapped = mapApiToRows(data);
        if (mapped) {
          setRows(mapped.rows);
          setPeriods(mapped.periods);
          setTodayLeft(mapped.todayLeft);
        }
      })
      .catch(() => {
        // fetch failed — keep fallback data
      });
  }, []);

  return (
    <div className="h-[calc(100vh-4rem)] flex flex-col bg-surface-bright w-full overflow-hidden">
      
      {/* Toolbar */}
      <div className="px-6 py-3 border-b border-surface-border bg-surface-container-lowest flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <button className="flex items-center gap-2 px-3 py-1.5 bg-surface-container-lowest hover:bg-surface-container-low rounded-lg border border-surface-border text-[13px] font-medium text-on-surface transition-colors">
            <Filter size={16} /> Filter
          </button>
          
          <div className="h-6 w-px bg-surface-border mx-1"></div>
          
          <div className="flex items-center bg-surface-container-low rounded-lg border border-surface-border p-0.5">
            <button className="px-4 py-1.5 rounded-sm bg-surface-container-lowest text-[13px] font-medium text-on-surface shadow-sm">Days</button>
            <button className="px-4 py-1.5 rounded-sm text-[13px] font-medium text-on-surface-variant hover:text-on-surface">Weeks</button>
            <button className="px-4 py-1.5 rounded-sm text-[13px] font-medium text-on-surface-variant hover:text-on-surface">Months</button>
          </div>
        </div>
        
        <div className="flex items-center gap-5 text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider">
          <div className="flex items-center gap-2"><div className="w-4 h-1 bg-surface-border rounded-full"></div> Baseline</div>
          <div className="flex items-center gap-2"><div className="w-3 h-3 bg-primary rounded-sm"></div> Actual</div>
        </div>
      </div>

      {/* Split View */}
      <div className="flex-1 flex overflow-hidden bg-surface">
        
        {/* Left: WBS Table */}
        <div className="w-[40%] flex flex-col border-r border-surface-border bg-surface-container-lowest shrink-0 z-10 shadow-[2px_0_8px_rgba(0,0,0,0.02)]">
          
          {/* Header */}
          <div className="flex border-b border-surface-border bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider sticky top-0 z-20">
            <div className="px-4 py-3 w-32 shrink-0 border-r border-surface-border">WBS Code</div>
            <div className="px-4 py-3 flex-1 border-r border-surface-border">Activity Name</div>
            <div className="px-4 py-3 w-20 text-right shrink-0 border-r border-surface-border">% Comp</div>
            <div className="px-4 py-3 w-32 shrink-0">Status</div>
          </div>

          {/* Body */}
          <div className="flex-1 overflow-y-auto">
            {rows.map(renderTableRow)}
          </div>
        </div>

        {/* Right: Gantt Chart */}
        <div className="flex-1 overflow-x-auto overflow-y-hidden bg-surface-bright relative">
          
          {/* Grid Background */}
          <div 
            className="absolute inset-0 pointer-events-none" 
            style={{ 
              backgroundSize: '40px 100%', 
              backgroundImage: 'linear-gradient(to right, var(--color-surface-border) 1px, transparent 1px)' 
            }}
          ></div>

          {/* Timeline Header */}
          <div className="flex border-b border-surface-border bg-surface-container-lowest text-[11px] font-semibold text-on-surface-variant sticky top-0 z-20 min-w-max h-[45px]">
            <div className="absolute inset-0 flex items-end pb-2 px-1">
              {periods.map((period, i) => (
                <div key={i} className="w-[200px] shrink-0 border-l border-surface-border pl-2">{period.label}</div>
              ))}
            </div>
          </div>

          {/* Timeline Body Rows */}
          <div className="min-w-max relative" style={{ minHeight: 'calc(100% - 45px)' }}>
            {rows.map(renderGanttRow)}

            {/* Today Marker */}
            <div className="absolute top-0 bottom-0 w-[2px] bg-status-review/50 border-l border-dashed border-status-review z-10" style={{ left: `${todayLeft}px` }}>
              <div className="absolute -top-5 -left-6 bg-status-review text-on-error font-semibold text-[10px] px-2 py-0.5 rounded tracking-wider">TODAY</div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
