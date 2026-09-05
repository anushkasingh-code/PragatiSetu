'use client';

import { apiFetchSafe } from '@/lib/api';
import { notifyAppDataRefresh, useAppDataRefresh } from '@/lib/app-sync';
import { Suspense } from 'react';
import {
  FALLBACK_WBS_CODE,
  getPendingFallbackReviews,
  resolveFallbackReview,
  type FallbackReviewRecord,
} from '@/lib/report-fallback';
import { getDeletedProjectCodes, isProjectDeleted, FALLBACK_PROJECTS } from '@/lib/projects';
import {
  Filter,
  Mic,
  BrainCircuit,
  CheckCircle2,
  AlertTriangle,
  Check,
  ArrowRightLeft,
  X,
  ChevronLeft,
  ChevronRight,
  Edit3,
  RotateCcw,
} from 'lucide-react';
import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

type ExtractedEvent = {
  event_id: string;
  report_id: string;
  raw_text: string;
  action?: string | null;
  object?: string | null;
  identifier?: string | null;
  location?: string | null;
  status?: string | null;
};

type MatchDecision = {
  event_id: string;
  decision: string;
  top_activity_id?: string | null;
  match_confidence: number;
  reasons?: string[] | null;
};

type CandidateScore = {
  activity_id: string;
  rank: number;
  overall_score: number;
};

type Activity = {
  activity_id: string;
  description: string;
  equipment_or_line_id?: string | null;
};

type ReviewItem = {
  event: ExtractedEvent;
  decision: MatchDecision;
  candidates: CandidateScore[];
  activities: Record<string, Activity>;
  isFallback?: boolean;
};

const PENDING_DECISIONS = new Set(['HUMAN_REVIEW', 'UNPLANNED_REVIEW', 'CONFLICT_REVIEW']);

function fallbackToReviewItem(record: FallbackReviewRecord): ReviewItem {
  const activities: Record<string, Activity> = {
    [FALLBACK_WBS_CODE]: {
      activity_id: FALLBACK_WBS_CODE,
      description: 'Spool Erection — Rack B Piping Package',
      equipment_or_line_id: FALLBACK_WBS_CODE,
    },
    'PIP-204-018': {
      activity_id: 'PIP-204-018',
      description: 'Hydrotest — Rack B Piping Package',
      equipment_or_line_id: 'PIP-204-018',
    },
  };

  return {
    event: {
      event_id: record.event_id,
      report_id: record.report_id,
      raw_text: record.raw_text,
      identifier: record.identifier,
      action: record.action,
      object: record.object,
      location: record.location,
      status: record.status,
    },
    decision: {
      event_id: record.event_id,
      decision: record.decision,
      top_activity_id: record.top_activity_id,
      match_confidence: record.match_confidence,
      reasons: record.reasons,
    },
    candidates: record.candidates,
    activities,
    isFallback: true,
  };
}

async function fetchPendingReviews(projectId: string): Promise<ReviewItem[]> {
  if (!projectId || isProjectDeleted(projectId)) {
    return [];
  }
  // 1. Fetch live pending reviews from fast aggregated backend endpoint
  const pendingRes = await apiFetchSafe<ReviewItem[]>(`/projects/${encodeURIComponent(projectId)}/reviews/pending?limit=1000`);
  if (pendingRes.ok && Array.isArray(pendingRes.data)) {
    if (pendingRes.data.length > 0) {
      return pendingRes.data;
    }
    // Only return fallback items specifically created for this project
    return getPendingFallbackReviews(projectId).map(fallbackToReviewItem);
  }

  // 2. If network failed, only fallback if project is not deleted
  const fallbackItems = getPendingFallbackReviews(projectId).map(fallbackToReviewItem);
  return fallbackItems;
}

function ReviewQueueContent() {
  const searchParams = useSearchParams();

  const [activeProject, setActiveProject] = useState<{
    project_id: string;
    name: string;
    displayCode: string;
  } | null>(null);

  const [items, setItems] = useState<ReviewItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [selectedActivityId, setSelectedActivityId] = useState<string | null>(null);
  const [isModifying, setIsModifying] = useState(false);
  const [customWbsCode, setCustomWbsCode] = useState('');
  const [modifyNote, setModifyNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  const resolveActiveProject = useCallback(async () => {
    const deleted = getDeletedProjectCodes();
    const res = await apiFetchSafe<{ project_id: string; name: string; description?: string }[]>('/projects');
    let available: { project_id: string; name: string; displayCode: string }[] = [];

    if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
      available = res.data
        .filter((p) => !deleted.has(p.project_id))
        .map((p) => ({
          project_id: p.project_id,
          name: p.name,
          displayCode: p.project_id === 'PROJ-ALPHA' ? '24P201' : p.project_id,
        }));
    }

    if (available.length === 0 && (!res.ok || res.data.length === 0)) {
      const activeFallbacks = FALLBACK_PROJECTS.filter((p) => !deleted.has(p.code));
      available = activeFallbacks.map((p) => ({
        project_id: p.code,
        name: p.name,
        displayCode: p.displayCode,
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

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const currentProj = await resolveActiveProject();
      if (!currentProj) {
        setItems([]);
        setCurrentIndex(0);
        return;
      }
      const pending = await fetchPendingReviews(currentProj.project_id);
      setItems(pending);
      setCurrentIndex((prev) => (pending.length === 0 ? 0 : Math.min(prev, pending.length - 1)));
    } catch {
      setItems([]);
      setCurrentIndex(0);
      setError('Failed to load review queue.');
    } finally {
      setLoading(false);
    }
  }, [resolveActiveProject]);

  useEffect(() => {
    void loadQueue();
  }, [loadQueue]);

  useAppDataRefresh(loadQueue);

  const currentItem = items[currentIndex] ?? null;
  const topCandidate = currentItem?.candidates[0] ?? null;
  const activeActivityId = selectedActivityId ?? currentItem?.decision.top_activity_id ?? topCandidate?.activity_id ?? null;

  useEffect(() => {
    setSelectedActivityId(null);
    setIsModifying(false);
    setCustomWbsCode('');
    setModifyNote('');
  }, [currentIndex, currentItem?.event.event_id]);

  const handleDecision = async (
    decision: 'ACCEPT' | 'REJECT' | 'UNPLANNED',
    overrideActivityId?: string,
    overrideReason?: string
  ) => {
    if (!currentItem) return;
    setActionLoading(true);
    setError(null);
    try {
      const chosenActivityId = overrideActivityId || activeActivityId;
      const chosenReason =
        overrideReason ||
        (decision === 'ACCEPT'
          ? 'Planner confirmed match'
          : decision === 'UNPLANNED'
          ? 'Planner marked as unplanned event'
          : 'Planner rejected match');

      if (currentItem.isFallback) {
        resolveFallbackReview(currentItem.event.event_id);
        setItems((prev) => {
          const next = prev.filter((it) => it.event.event_id !== currentItem.event.event_id);
          setCurrentIndex((idx) => (next.length === 0 ? 0 : Math.min(idx, next.length - 1)));
          return next;
        });
        notifyAppDataRefresh({ source: 'review-queue' });
        await loadQueue();
        return;
      }

      const result = await apiFetchSafe(`/reviews/${currentItem.event.event_id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision,
          selected_activity_id: decision === 'ACCEPT' ? chosenActivityId : undefined,
          reason: chosenReason,
        }),
      });

      if (!result.ok) {
        setError(`Review action failed: ${result.error}`);
        return;
      }
      setItems((prev) => {
        const next = prev.filter((it) => it.event.event_id !== currentItem.event.event_id);
        setCurrentIndex((idx) => (next.length === 0 ? 0 : Math.min(idx, next.length - 1)));
        return next;
      });
      notifyAppDataRefresh({ source: 'review-queue' });
      await loadQueue();
    } catch {
      setError('Failed to submit review decision.');
    } finally {
      setActionLoading(false);
      setIsModifying(false);
    }
  };

  const handleSwitchCandidate = (activityId: string) => {
    setSelectedActivityId(activityId);
  };

  const handleResetQueue = async () => {
    setActionLoading(true);
    setError(null);
    try {
      await apiFetchSafe('/reviews/reset', { method: 'POST' });
      notifyAppDataRefresh({ source: 'review-queue' });
      await loadQueue();
    } catch {
      setError('Failed to reset review items.');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="p-6 h-[calc(100vh-4rem)] flex flex-col gap-6 max-w-[1600px] mx-auto w-full">
      <div className="flex justify-between items-end shrink-0">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
              PragatiSetu Validation
            </span>
            <span className="text-[11px] font-mono text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded border border-surface-border font-semibold">
              {activeProject ? `${activeProject.name} (${activeProject.displayCode})` : 'No Active Project'}
            </span>
          </div>
          <h2 className="text-[24px] font-semibold text-on-surface">Review Queue</h2>
          <p className="text-[14px] text-on-surface-variant mt-0.5">Resolve AI-extracted field events against the WBS.</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded bg-surface-container-high text-on-surface text-[11px] font-semibold border border-surface-border uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-status-review"></span>
            {loading ? '...' : `${items.length} PENDING`}
          </span>
          <button
            onClick={() => void loadQueue()}
            className="px-3 py-1.5 border border-surface-border rounded-lg text-[12px] font-bold hover:bg-surface-container transition-colors flex items-center gap-1.5 bg-surface-container-lowest text-on-surface cursor-pointer"
          >
            <Filter size={14} /> Refresh
          </button>
          <button
            onClick={handleResetQueue}
            disabled={actionLoading}
            title="Reset test events back to review queue"
            className="px-3 py-1.5 border border-surface-border rounded-lg text-[12px] font-bold hover:bg-surface-container transition-colors flex items-center gap-1.5 bg-surface-container-lowest text-on-surface-variant cursor-pointer disabled:opacity-50"
          >
            <RotateCcw size={14} /> Reset Queue
          </button>
        </div>
      </div>

      {error && (
        <p className="text-[14px] text-error bg-error-container/30 border border-error/20 rounded-lg px-4 py-2">{error}</p>
      )}

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-on-surface-variant">Loading review queue...</div>
      ) : !currentItem ? (
        <div className="flex-1 flex flex-col items-center justify-center text-on-surface-variant gap-4 bg-surface-container-lowest border border-surface-border rounded-xl p-8 max-w-md mx-auto my-auto text-center animate-fadeIn">
          <div className="w-12 h-12 rounded-full bg-status-completed/10 text-status-completed flex items-center justify-center">
            <CheckCircle2 size={28} />
          </div>
          <div>
            <h3 className="text-[18px] font-semibold text-on-surface mb-1">All Reviews Completed!</h3>
            <p className="text-[13px] text-on-surface-variant leading-relaxed">
              All field events have been processed and applied to the WBS baseline schedule.
            </p>
          </div>
          <button
            onClick={handleResetQueue}
            disabled={actionLoading}
            className="mt-2 px-5 py-2.5 bg-primary text-on-primary rounded-lg text-[13px] font-bold hover:bg-primary/90 transition-colors flex items-center gap-2 cursor-pointer shadow-sm disabled:opacity-50"
          >
            <RotateCcw size={16} /> Reset Demo Items for Testing
          </button>
        </div>
      ) : (
        <div className="flex-1 grid grid-cols-1 xl:grid-cols-12 gap-6 min-h-0">
          <div className="xl:col-span-5 flex flex-col gap-4 min-h-0">
            <div className="bg-surface-container-lowest border border-surface-border rounded-xl shadow-sm p-5 flex flex-col h-full overflow-y-auto">
              <div className="flex justify-between items-center mb-5 border-b border-surface-border pb-4">
                <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                  <Mic className="text-primary" size={20} />
                  Field Transcript
                </h3>
                <span className="text-[13px] font-mono text-on-surface-variant bg-surface-container px-2 py-1 rounded">
                  ID: {currentItem.event.event_id}
                </span>
              </div>

              <div className="bg-surface-container p-5 rounded-lg mb-6 border-l-4 border-primary">
                <p className="text-[16px] text-on-surface italic leading-relaxed">
                  &quot;{currentItem.event.raw_text}&quot;
                </p>
              </div>

              <h4 className="text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider mb-4">Extracted Data</h4>

              <div className="grid grid-cols-2 gap-y-5 gap-x-6">
                <div>
                  <span className="block text-[12px] font-bold text-outline mb-1.5">IDENTIFIER</span>
                  <span className="font-mono text-[13px] text-on-surface font-medium">
                    {currentItem.event.identifier ?? '—'}
                  </span>
                </div>
                <div>
                  <span className="block text-[12px] font-bold text-outline mb-1.5">ACTION</span>
                  <span className="text-[14px] text-on-surface">{currentItem.event.action ?? '—'}</span>
                </div>
                <div>
                  <span className="block text-[12px] font-bold text-outline mb-1.5">OBJECT</span>
                  <span className="text-[14px] text-on-surface">{currentItem.event.object ?? '—'}</span>
                </div>
                <div>
                  <span className="block text-[12px] font-bold text-outline mb-1.5">LOCATION</span>
                  <span className="text-[14px] text-on-surface">{currentItem.event.location ?? '—'}</span>
                </div>
                <div className="col-span-2">
                  <span className="block text-[12px] font-bold text-outline mb-1.5">IMPLIED STATUS</span>
                  {currentItem.event.status ? (
                    <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-status-completed/10 text-status-completed text-[12px] font-bold border border-status-completed/20 uppercase">
                      <CheckCircle2 size={14} /> {currentItem.event.status}
                    </span>
                  ) : (
                    <span className="text-[14px] text-on-surface-variant">—</span>
                  )}
                </div>
              </div>

              <div className="mt-auto pt-6">
                <button
                  onClick={() => void handleDecision('UNPLANNED')}
                  disabled={actionLoading}
                  className="w-full py-2.5 bg-surface-container-low hover:bg-surface-container-high border border-surface-border rounded-lg text-on-surface text-[14px] font-bold transition-colors flex items-center justify-center gap-2 disabled:opacity-70 cursor-pointer"
                >
                  <AlertTriangle size={18} /> Mark as Unplanned Event
                </button>
              </div>
            </div>
          </div>

          <div className="xl:col-span-7 flex flex-col min-h-0 bg-surface-container-lowest border border-surface-border rounded-xl shadow-sm">
            <div className="p-5 border-b border-surface-border flex justify-between items-center bg-surface-bright rounded-t-xl shrink-0">
              <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                <BrainCircuit className="text-secondary" size={20} />
                AI Match Candidates
              </h3>
              <span className="text-[12px] font-bold text-on-surface-variant">
                {currentItem.candidates.length} Candidate{currentItem.candidates.length === 1 ? '' : 's'} Found
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-4">
              {currentItem.candidates.length === 0 ? (
                <p className="text-[14px] text-on-surface-variant">No match candidates available for this event.</p>
              ) : (
                currentItem.candidates.map((candidate, idx) => {
                  const activity = currentItem.activities[candidate.activity_id];
                  const isTop = idx === 0;
                  const isSelected = candidate.activity_id === activeActivityId;

                  if (isTop) {
                    return (
                      <div
                        key={candidate.activity_id}
                        className="border border-primary bg-primary-fixed/10 rounded-lg p-5 relative overflow-hidden transition-all shadow-sm"
                      >
                        <div className="absolute top-0 right-0 bg-primary text-on-primary text-[11px] font-bold px-3 py-1 rounded-bl-lg tracking-wider">
                          TOP MATCH
                        </div>

                        <div className="flex justify-between items-start mb-4 pr-24">
                          <div>
                            <span className="font-mono text-[13px] font-semibold text-primary block mb-1">
                              WBS: {candidate.activity_id}
                            </span>
                            <h4 className="text-[16px] font-medium text-on-surface">
                              {activity?.description ?? 'Activity details unavailable'}
                            </h4>
                          </div>
                          <div className="text-right">
                            <div className="text-[24px] font-bold text-status-completed leading-none mb-1">
                              {Math.round(candidate.overall_score)}%
                            </div>
                            <div className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
                              CONFIDENCE
                            </div>
                          </div>
                        </div>

                        {currentItem.decision.reasons && currentItem.decision.reasons.length > 0 && (
                          <div className="bg-surface-container-lowest p-4 rounded border border-surface-border mb-5 text-[14px] text-on-surface-variant leading-relaxed">
                            <strong className="text-on-surface text-[12px] font-bold block mb-1.5">AI Reasoning:</strong>
                            {currentItem.decision.reasons.join(' ')}
                          </div>
                        )}

                        <div className="flex gap-3">
                          <button
                            onClick={() => void handleDecision('ACCEPT')}
                            disabled={actionLoading || !activeActivityId}
                            className="flex-1 bg-primary hover:bg-primary-container text-on-primary py-2.5 rounded-lg text-[14px] font-bold transition-colors flex justify-center items-center gap-2 disabled:opacity-70 cursor-pointer"
                          >
                            <Check size={18} /> ACCEPT MATCH
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              const nextState = !isModifying;
                              setIsModifying(nextState);
                              if (nextState && !customWbsCode && activeActivityId) {
                                setCustomWbsCode(activeActivityId);
                              }
                            }}
                            className={`px-6 py-2.5 border rounded-lg text-[14px] font-bold transition-colors cursor-pointer flex items-center gap-1.5 ${
                              isModifying
                                ? 'bg-primary/10 border-primary text-primary'
                                : 'bg-surface-container-low hover:bg-surface-container-high border-surface-border text-on-surface'
                            }`}
                          >
                            <Edit3 size={16} /> MODIFY
                          </button>
                        </div>

                        {/* Expandable Manual Modification Card */}
                        {isModifying && (
                          <div className="mt-4 p-4 rounded-xl border border-primary/30 bg-primary/5 space-y-3 animate-fadeIn">
                            <div className="flex justify-between items-center">
                              <span className="text-[12px] font-bold uppercase tracking-wider text-primary">Manual Match Override</span>
                              <button
                                type="button"
                                onClick={() => setIsModifying(false)}
                                className="text-on-surface-variant hover:text-on-surface text-[12px] cursor-pointer"
                              >
                                Cancel
                              </button>
                            </div>
                            <div>
                              <label className="text-[11px] font-bold uppercase text-on-surface-variant block mb-1">
                                Target WBS Activity Code
                              </label>
                              <input
                                type="text"
                                value={customWbsCode}
                                onChange={(e) => setCustomWbsCode(e.target.value)}
                                placeholder="e.g. 24P201 or CIV-101"
                                className="w-full bg-surface-container-lowest border border-surface-border rounded-lg px-3 py-1.5 text-[13px] font-mono font-bold text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                              />
                            </div>
                            <div>
                              <label className="text-[11px] font-bold uppercase text-on-surface-variant block mb-1">
                                Supervisor Override Reason
                              </label>
                              <input
                                type="text"
                                value={modifyNote}
                                onChange={(e) => setModifyNote(e.target.value)}
                                placeholder="e.g. Activity re-assigned based on site visual inspection"
                                className="w-full bg-surface-container-lowest border border-surface-border rounded-lg px-3 py-1.5 text-[13px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary"
                              />
                            </div>
                            <div className="flex justify-end gap-2 pt-1">
                              <button
                                type="button"
                                onClick={() => void handleDecision('ACCEPT', customWbsCode, modifyNote || 'Manual WBS override by supervisor')}
                                disabled={actionLoading || !customWbsCode.trim()}
                                className="px-4 py-2 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50 cursor-pointer"
                              >
                                Save &amp; Confirm Match
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  }

                  return (
                    <div
                      key={candidate.activity_id}
                      className={`border rounded-lg p-5 transition-all hover:border-outline-variant ${
                        isSelected ? 'border-primary bg-primary-fixed/5' : 'border-surface-border bg-surface-container-lowest'
                      }`}
                    >
                      <div className="flex justify-between items-start mb-3">
                        <div>
                          <span className="font-mono text-[13px] font-semibold text-secondary block mb-1">
                            WBS: {candidate.activity_id}
                          </span>
                          <h4 className="text-[14px] font-medium text-on-surface">
                            {activity?.description ?? 'Activity details unavailable'}
                          </h4>
                        </div>
                        <div className="text-right">
                          <div className="text-[20px] font-bold text-status-review leading-none">
                            {Math.round(candidate.overall_score)}%
                          </div>
                        </div>
                      </div>

                      <button
                        onClick={() => handleSwitchCandidate(candidate.activity_id)}
                        className="w-full py-2 bg-surface-container-low hover:bg-surface-container-high border border-surface-border text-on-surface rounded-lg text-[14px] font-bold transition-colors flex justify-center items-center gap-2"
                      >
                        <ArrowRightLeft size={16} /> SWITCH TO THIS
                      </button>
                    </div>
                  );
                })
              )}
            </div>

            <div className="p-4 border-t border-surface-border bg-surface-bright rounded-b-xl flex justify-between items-center shrink-0">
              <button
                onClick={() => void handleDecision('REJECT')}
                disabled={actionLoading}
                className="text-error hover:bg-error/10 px-4 py-2 rounded-lg text-[14px] font-bold transition-colors flex items-center gap-2 border border-error/20 bg-error-container/50 disabled:opacity-70"
              >
                <X size={18} /> REJECT ALL
              </button>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
                  disabled={currentIndex === 0}
                  className="p-2 border border-surface-border rounded hover:bg-surface-container transition-colors text-on-surface-variant disabled:opacity-50"
                >
                  <ChevronLeft size={18} />
                </button>
                <span className="text-[13px] font-mono font-medium">
                  {items.length === 0 ? '0 of 0' : `${currentIndex + 1} of ${items.length}`}
                </span>
                <button
                  onClick={() => setCurrentIndex((i) => Math.min(items.length - 1, i + 1))}
                  disabled={currentIndex >= items.length - 1}
                  className="p-2 border border-surface-border rounded hover:bg-surface-container transition-colors text-on-surface-variant disabled:opacity-50"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReviewQueue() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-on-surface-variant">Loading review queue...</div>}>
      <ReviewQueueContent />
    </Suspense>
  );
}
