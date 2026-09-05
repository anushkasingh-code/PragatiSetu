'use client';

import React, { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import { apiFetchSafe } from '@/lib/api';
import { useAppDataRefresh, notifyAppDataRefresh } from '@/lib/app-sync';
import { parseServerDate } from '@/lib/date';
import { getDeletedProjectCodes } from '@/lib/projects';
import {
  Search,
  Calendar,
  Filter,
  Download,
  History,
  Trash2,
  PersonStanding,
  Check,
  X,
  FileCheck,
  CheckCircle2,
} from 'lucide-react';

interface AuditRecord {
  id: string;
  type: 'AUTO_LINK' | 'OVERRIDE' | 'VERIFIED';
  time: string;
  daysAgo: number;
  description: string;
  confidence: number;
  user: string;
  hash: string;
  activityCode: string;
  activityName: string;
  wbs: string;
  prevStatus: string;
  prevPercent: number;
  prevStart: string;
  newStatus: string;
  newPercent: number;
  newStart: string;
}

function AuditTrailContent() {
  const searchParams = useSearchParams();

  const [activeProject, setActiveProject] = useState<{
    project_id: string;
    name: string;
    displayCode: string;
  } | null>(null);

  const [search, setSearch] = useState('');
  const [dateFilter, setDateFilter] = useState<'7d' | '30d' | 'all'>('7d');
  const [decisionFilter, setDecisionFilter] = useState<'all' | 'AUTO_LINK' | 'OVERRIDE' | 'VERIFIED'>('all');
  const [visibleCount, setVisibleCount] = useState(5);
  const [isDateOpen, setIsDateOpen] = useState(false);
  const [isDecisionOpen, setIsDecisionOpen] = useState(false);
  const [exportNotice, setExportNotice] = useState(false);
  const [clearNotice, setClearNotice] = useState(false);
  const [liveAuditData, setLiveAuditData] = useState<AuditRecord[]>([]);

  const resolveActiveProject = useCallback(async () => {
    const deleted = getDeletedProjectCodes();
    const res = await apiFetchSafe<{ project_id: string; name: string }[]>('/projects');
    if (!res.ok || !Array.isArray(res.data)) {
      setActiveProject(null);
      return null;
    }
    const available = res.data
      .filter((p) => !deleted.has(p.project_id))
      .map((p) => ({
        project_id: p.project_id,
        name: p.name,
        displayCode: p.project_id === 'PROJ-ALPHA' ? '24P201' : p.project_id,
      }));

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

  const fetchAuditTrail = useCallback(async () => {
    const proj = await resolveActiveProject();
    if (!proj) {
      setLiveAuditData([]);
      return;
    }

    // 1. Fetch live audit records from backend scoped to project
    const auditRes = await apiFetchSafe<any[]>(`/audit?project_id=${encodeURIComponent(proj.project_id)}`);
    if (!auditRes.ok || !Array.isArray(auditRes.data)) {
      setLiveAuditData([]);
      return;
    }

    // 2. Fetch activities metadata for descriptions & WBS codes for active project
    const actRes = await apiFetchSafe<any[]>(`/projects/${encodeURIComponent(proj.project_id)}/activities`);
    const actMap = new Map<string, { desc: string; wbs: string }>();
    if (actRes.ok && Array.isArray(actRes.data)) {
      actRes.data.forEach((a) => {
        actMap.set(a.activity_id, {
          desc: a.description || a.activity_id,
          wbs: a.wbs_id || a.discipline || 'Civil & Earthworks',
        });
      });
    }

    const now = new Date().getTime();
    const liveMapped: AuditRecord[] = auditRes.data.map((rec) => {
      const recDate = parseServerDate(rec.timestamp);
      const diffDays = Math.max(0, Math.floor((now - recDate.getTime()) / (1000 * 60 * 60 * 24)));
      const timeStr = recDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

      let decisionType: 'AUTO_LINK' | 'OVERRIDE' | 'VERIFIED' = 'AUTO_LINK';
      if (rec.system_decision === 'OVERRIDE') decisionType = 'OVERRIDE';
      else if (rec.system_decision === 'HUMAN_REVIEW' || (rec.reviewer && !rec.reviewer.includes('SYSTEM'))) {
        decisionType = 'VERIFIED';
      }

      const actInfo = actMap.get(rec.activity_id);

      return {
        id: rec.audit_id,
        type: decisionType,
        time: `${recDate.toLocaleDateString([], { month: 'short', day: 'numeric' })}, ${timeStr}`,
        daysAgo: diffDays,
        description: rec.reason || `Progress update applied for activity ${rec.activity_id}.`,
        confidence: Math.round(rec.confidence || 90),
        user: rec.reviewer && rec.reviewer.includes('SYSTEM') ? 'System (AI Auto-Link)' : 'Site Planner (Human Review)',
        hash: rec.report_id ? rec.report_id.slice(-8) : rec.audit_id.slice(-8),
        activityCode: rec.activity_id,
        activityName: actInfo?.desc || `Activity ${rec.activity_id}`,
        wbs: actInfo?.wbs || 'Civil & Earthworks',
        prevStatus: rec.previous_value?.status || 'NOT_STARTED',
        prevPercent: Math.round(rec.previous_value?.percent_complete || 0),
        prevStart: rec.previous_value?.actual_start || '--/--/----',
        newStatus: rec.new_value?.status || 'IN_PROGRESS',
        newPercent: Math.round(rec.new_value?.percent_complete || 0),
        newStart: rec.new_value?.actual_start || recDate.toLocaleDateString([], { day: '2-digit', month: '2-digit', year: 'numeric' }),
      };
    });

    setLiveAuditData(liveMapped);
  }, [resolveActiveProject]);

  useEffect(() => {
    void fetchAuditTrail();
  }, [fetchAuditTrail]);

  useAppDataRefresh(fetchAuditTrail);

  // Filter records
  const filtered = liveAuditData.filter((r) => {
    if (search.trim()) {
      const q = search.toLowerCase();
      const match =
        r.activityCode.toLowerCase().includes(q) ||
        r.activityName.toLowerCase().includes(q) ||
        r.wbs.toLowerCase().includes(q) ||
        r.user.toLowerCase().includes(q);
      if (!match) return false;
    }
    if (dateFilter === '7d' && r.daysAgo > 7) return false;
    if (dateFilter === '30d' && r.daysAgo > 30) return false;
    if (decisionFilter !== 'all' && r.type !== decisionFilter) return false;
    return true;
  });

  const displayedRecords = filtered.slice(0, visibleCount);

  const handleExport = () => {
    const headers = ['Audit ID', 'Decision Type', 'Time', 'Activity Code', 'Activity Name', 'WBS', 'User', 'Confidence', 'Previous Status', 'Previous %', 'New Status', 'New %', 'Hash'];
    const rows = filtered.map((r) => [
      r.id,
      r.type,
      r.time,
      r.activityCode,
      `"${r.activityName}"`,
      r.wbs,
      `"${r.user}"`,
      `${r.confidence}%`,
      r.prevStatus,
      `${r.prevPercent}%`,
      r.newStatus,
      `${r.newPercent}%`,
      r.hash,
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `pragatisetu-audit-trail-${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    link.remove();

    setExportNotice(true);
    setTimeout(() => setExportNotice(false), 3000);
  };

  const handleClearAuditTrail = async () => {
    if (!activeProject) return;
    if (!confirm(`Clear all audit trail records for ${activeProject.name}?`)) return;
    try {
      await apiFetchSafe(`/audit/clear?project_id=${encodeURIComponent(activeProject.project_id)}`, { method: 'POST' });
      setLiveAuditData([]);
      notifyAppDataRefresh({ source: 'audit-trail' });
      setClearNotice(true);
      setTimeout(() => setClearNotice(false), 3500);
    } catch {
      setLiveAuditData([]);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto w-full space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
              PragatiSetu Compliance
            </span>
            <span className="text-[11px] font-mono text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded border border-surface-border font-semibold">
              {activeProject ? `${activeProject.name} (${activeProject.displayCode})` : 'No Active Project'}
            </span>
          </div>
          <h2 className="text-[28px] font-bold text-on-surface leading-tight">Audit &amp; Compliance Trail</h2>
          <p className="text-[14px] text-on-surface-variant mt-0.5">
            Immutable ledger of schedule modifications, AI linkages, and supervisor overrides.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 bg-surface-container-lowest p-2 rounded-xl border border-surface-border shadow-sm">
          {/* Search Box */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline" size={15} />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Filter Activity ID..."
              className="pl-8 pr-3 py-1.5 rounded-lg bg-surface-container-low text-on-surface focus:outline-none focus:ring-2 focus:ring-primary text-[13px] w-40"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch('')}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface cursor-pointer"
              >
                <X size={13} />
              </button>
            )}
          </div>

          <div className="h-5 w-px bg-surface-border"></div>

          {/* Date Filter Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setIsDateOpen(!isDateOpen);
                setIsDecisionOpen(false);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-surface-container-low transition-colors font-mono text-[12px] text-on-surface-variant font-medium cursor-pointer"
            >
              <Calendar size={14} />
              <span>{dateFilter === '7d' ? 'Last 7 Days' : dateFilter === '30d' ? 'Last 30 Days' : 'All Dates'}</span>
            </button>
            {isDateOpen && (
              <div className="absolute left-0 mt-2 w-36 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-30 p-1 space-y-0.5 animate-fadeIn">
                {[
                  { id: '7d', label: 'Last 7 Days' },
                  { id: '30d', label: 'Last 30 Days' },
                  { id: 'all', label: 'All Dates' },
                ].map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => {
                      setDateFilter(d.id as typeof dateFilter);
                      setIsDateOpen(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-md text-[12px] flex items-center justify-between cursor-pointer ${
                      dateFilter === d.id ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-surface-container-low text-on-surface'
                    }`}
                  >
                    <span>{d.label}</span>
                    {dateFilter === d.id && <Check size={13} className="text-primary" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Decision Type Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setIsDecisionOpen(!isDecisionOpen);
                setIsDateOpen(false);
              }}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-surface-container-low transition-colors font-mono text-[12px] text-on-surface-variant font-medium cursor-pointer"
            >
              <Filter size={14} />
              <span>{decisionFilter === 'all' ? 'All Decisions' : decisionFilter}</span>
            </button>
            {isDecisionOpen && (
              <div className="absolute left-0 mt-2 w-44 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-30 p-1 space-y-0.5 animate-fadeIn">
                {[
                  { id: 'all', label: 'All Decisions' },
                  { id: 'AUTO_LINK', label: 'AUTO_LINK' },
                  { id: 'OVERRIDE', label: 'OVERRIDE' },
                  { id: 'VERIFIED', label: 'VERIFIED' },
                ].map((dec) => (
                  <button
                    key={dec.id}
                    type="button"
                    onClick={() => {
                      setDecisionFilter(dec.id as typeof decisionFilter);
                      setIsDecisionOpen(false);
                    }}
                    className={`w-full text-left px-2.5 py-1.5 rounded-md text-[12px] flex items-center justify-between cursor-pointer ${
                      decisionFilter === dec.id ? 'bg-primary/10 text-primary font-bold' : 'hover:bg-surface-container-low text-on-surface'
                    }`}
                  >
                    <span>{dec.label}</span>
                    {decisionFilter === dec.id && <Check size={13} className="text-primary" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Export Button */}
          <button
            type="button"
            onClick={handleExport}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-border bg-surface-container-low hover:bg-surface-container-high transition-colors font-mono text-[12px] text-on-surface font-semibold cursor-pointer"
            title="Export CSV audit trail"
          >
            <Download size={14} /> Export CSV
          </button>

          {/* Clear Audit Trail Button */}
          <button
            type="button"
            onClick={handleClearAuditTrail}
            disabled={liveAuditData.length === 0}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-surface-border bg-surface-container-low hover:bg-red-500/10 hover:text-red-600 hover:border-red-500/30 transition-colors font-mono text-[12px] text-on-surface-variant font-semibold cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
            title="Clear audit trail records for current project"
          >
            <Trash2 size={14} /> Clear History
          </button>
        </div>
      </div>

      {/* Export Confirmation Toast */}
      {exportNotice && (
        <div className="p-3 bg-status-completed/10 border border-status-completed/20 rounded-xl text-[13px] font-medium text-on-surface flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 size={16} className="text-status-completed" />
          <span>Audit trail exported successfully as CSV!</span>
        </div>
      )}

      {/* Clear Confirmation Toast */}
      {clearNotice && (
        <div className="p-3 bg-status-completed/10 border border-status-completed/20 rounded-xl text-[13px] font-medium text-on-surface flex items-center gap-2 animate-fadeIn">
          <CheckCircle2 size={16} className="text-status-completed" />
          <span>Audit trail cleared. Your workspace is fresh and ready for new work.</span>
        </div>
      )}

      {/* Audit Log Cards */}
      <div className="flex flex-col gap-5">
        {displayedRecords.length > 0 ? (
          displayedRecords.map((r) => (
            <div key={r.id} className="bg-surface-container-lowest rounded-xl border border-surface-border shadow-sm overflow-hidden flex flex-col md:flex-row">
              {/* Metadata Column */}
              <div className="w-full md:w-64 bg-surface-container-low p-5 border-b md:border-b-0 md:border-r border-surface-border flex flex-col justify-between shrink-0">
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span
                      className={`text-[10px] font-bold tracking-wider uppercase px-2 py-0.5 rounded ${
                        r.type === 'AUTO_LINK'
                          ? 'text-primary bg-primary/10 border border-primary/20'
                          : r.type === 'OVERRIDE'
                          ? 'text-status-conflict bg-status-conflict/10 border border-status-conflict/20'
                          : 'text-status-completed bg-status-completed/10 border border-status-completed/20'
                      }`}
                    >
                      {r.type}
                    </span>
                    <span className="font-mono text-[12px] text-on-surface-variant font-medium">{r.time}</span>
                  </div>
                  <p className="text-[13px] text-on-surface mt-2 leading-relaxed">{r.description}</p>
                </div>

                <div className="mt-4 pt-4 border-t border-surface-border/60 space-y-2 text-[12px]">
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">User</span>
                    <span className="font-mono text-on-surface font-semibold truncate max-w-[120px]" title={r.user}>
                      {r.user}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Confidence</span>
                    <span className="font-mono text-primary font-bold">{r.confidence}%</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-on-surface-variant">Checksum</span>
                    <span className="font-mono text-on-surface-variant text-[11px]">{r.hash}</span>
                  </div>
                </div>
              </div>

              {/* Data Diff Column */}
              <div className="flex-1 p-5">
                <div className="flex items-center gap-3 mb-5">
                  <div className="w-9 h-9 rounded-lg bg-surface-container-high flex items-center justify-center text-primary">
                    <History size={18} />
                  </div>
                  <div>
                    <h3 className="text-[16px] font-bold text-on-surface">
                      {r.activityCode} - {r.activityName}
                    </h3>
                    <p className="font-mono text-[12px] text-on-surface-variant">WBS: {r.wbs}</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* Previous State */}
                  <div className="border border-surface-border rounded-lg bg-surface-container-low p-4">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-on-surface-variant mb-3 flex items-center gap-1.5">
                      <History size={13} /> PREVIOUS STATE
                    </div>
                    <div className="space-y-1.5 text-[13px]">
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">Status</span>
                        <span className="font-mono text-on-surface font-semibold">{r.prevStatus}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">% Complete</span>
                        <span className="font-mono text-on-surface font-semibold">{r.prevPercent}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">Actual Start</span>
                        <span className="font-mono text-on-surface/60">{r.prevStart}</span>
                      </div>
                    </div>
                  </div>

                  {/* New State */}
                  <div className="border border-status-completed/30 rounded-lg bg-status-completed/5 p-4">
                    <div className="text-[10px] font-bold uppercase tracking-wider text-status-completed mb-3 flex items-center gap-1.5">
                      {r.type === 'AUTO_LINK' ? <FileCheck size={13} /> : <PersonStanding size={13} />}
                      {r.type === 'AUTO_LINK' ? 'AI PROPOSED & LINKED' : 'HUMAN FINAL RECORD'}
                    </div>
                    <div className="space-y-1.5 text-[13px]">
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">Status</span>
                        <span className="font-mono text-status-completed font-bold">{r.newStatus}</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">% Complete</span>
                        <span className="font-mono text-status-completed font-bold">{r.newPercent}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-on-surface-variant">Actual Start</span>
                        <span className="font-mono text-status-completed font-bold">{r.newStart}</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))
        ) : (
          <div className="p-10 text-center bg-surface-container-lowest border border-surface-border rounded-xl text-on-surface flex flex-col items-center justify-center max-w-md mx-auto space-y-3">
            <div className="w-12 h-12 rounded-full bg-surface-container text-on-surface-variant flex items-center justify-center">
              <History size={24} />
            </div>
            <h4 className="text-[16px] font-semibold">No audit activity yet.</h4>
            <p className="text-[13px] text-on-surface-variant leading-relaxed">
              Immutable audit records will automatically appear here when DPR reports are processed, schedule activities are linked, or supervisor reviews occur.
            </p>
          </div>
        )}

        {/* Load More Button */}
        {visibleCount < filtered.length ? (
          <div className="text-center mt-2">
            <button
              type="button"
              onClick={() => setVisibleCount((prev) => Math.min(filtered.length, prev + 3))}
              className="text-[12px] font-bold text-primary border border-primary/30 hover:bg-primary/5 transition-colors py-2 px-6 rounded-lg cursor-pointer"
            >
              Load More History ({filtered.length - visibleCount} remaining)...
            </button>
          </div>
        ) : (
          filtered.length > 0 && (
            <div className="text-center py-2 text-[12px] font-medium text-outline">
              All compliance log records displayed.
            </div>
          )
        )}
      </div>
    </div>
  );
}

export default function AuditTrail() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-on-surface-variant">Loading audit trail...</div>}>
      <AuditTrailContent />
    </Suspense>
  );
}
