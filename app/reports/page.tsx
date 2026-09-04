'use client';

import { notifyAppDataRefresh } from '@/lib/app-sync';
import { apiFetchSafe } from '@/lib/api';
import {
  buildFallbackExtraction,
  createFallbackReportRecord,
  delay,
  generateFallbackReportId,
  getFallbackReports,
  persistFallbackProcessing,
  type FallbackReportRecord,
} from '@/lib/report-fallback';
import { looksLikeSiteReport, readFileAsText } from '@/lib/report-validation';
import { UploadCloud, Mic, Sparkles, CheckCircle2, AlertTriangle, X } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';

type ReportUploadResponse = {
  report_id: string;
  processing_status: string;
};

type ReportResponse = {
  report_id: string;
  filename: string;
  processing_status: string;
  created_at: string;
  rejection_reason?: string | null;
};

type ExtractedEventResponse = {
  event_id: string;
};

type ExtractionResultResponse = {
  report_id: string;
  processing_status: string;
  event_count: number;
  events: ExtractedEventResponse[];
};

type PipelineStepStatus = 'waiting' | 'in_progress' | 'done';

type PipelineStep = {
  id: string;
  label: string;
  filename?: string;
  status: PipelineStepStatus;
  progress: number;
};

type HistoryRow = ReportResponse | FallbackReportRecord;

const TERMINAL_STATUSES = new Set(['PROCESSED', 'COMPLETED', 'FAILED', 'REJECTED', 'EVENTS_EXTRACTED']);

const INITIAL_PIPELINE: PipelineStep[] = [
  { id: 'upload', label: 'Uploading', status: 'waiting', progress: 0 },
  { id: 'validate', label: 'Validating structure', status: 'waiting', progress: 0 },
  { id: 'extract', label: 'Extracting Events', status: 'waiting', progress: 0 },
  { id: 'match', label: 'Matching to WBS', status: 'waiting', progress: 0 },
];

function isTerminalStatus(status: string) {
  return TERMINAL_STATUSES.has(status);
}

function formatHistoryStatus(status: string) {
  if (status === 'REJECTED' || status === 'FAILED') return 'Rejected';
  if (status === 'PROCESSED' || status === 'EVENTS_EXTRACTED' || status === 'COMPLETED') return 'Processed';
  if (status === 'VALIDATED') return 'Validated';
  return status;
}

function formatHistoryDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function stepLabel(step: PipelineStep) {
  if (step.id === 'upload' && step.filename) return `Uploading ${step.filename}`;
  return step.label;
}

function stepStatusText(step: PipelineStep) {
  if (step.status === 'done') return 'Done';
  if (step.status === 'in_progress') return `In Progress (${step.progress}%)`;
  return 'Waiting';
}

function stepStatusClass(step: PipelineStep) {
  if (step.status === 'done') return 'text-status-completed';
  if (step.status === 'in_progress') return 'text-status-review';
  return 'text-on-surface-variant';
}

function stepBarClass(step: PipelineStep) {
  if (step.status === 'done') return 'bg-status-completed';
  if (step.status === 'in_progress') return 'bg-status-review';
  return 'bg-surface-border';
}

function mergeHistory(apiReports: ReportResponse[], fallbackReports: FallbackReportRecord[]): HistoryRow[] {
  const apiIds = new Set(apiReports.map((r) => r.report_id));
  const merged: HistoryRow[] = [
    ...fallbackReports.filter((r) => !apiIds.has(r.report_id)),
    ...apiReports,
  ];
  return merged.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
}

export default function ReportsIngestionHub() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const projectId = searchParams.get('project_id') ?? 'PROJ-ALPHA';

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineCompleteRef = useRef(false);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [voiceProcessed, setVoiceProcessed] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const [reportId, setReportId] = useState<string | null>(null);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(INITIAL_PIPELINE);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [isPipelineActive, setIsPipelineActive] = useState(false);
  const [contentWarning, setContentWarning] = useState<string | null>(null);
  const [usedFallback, setUsedFallback] = useState(false);

  const updateStep = useCallback((id: string, patch: Partial<PipelineStep>) => {
    setPipelineSteps((prev) => prev.map((step) => (step.id === id ? { ...step, ...patch } : step)));
  }, []);

  const animateStep = useCallback(
    async (id: string, targetProgress: number) => {
      updateStep(id, { status: 'in_progress', progress: Math.min(targetProgress, 30) });
      await delay(400);
      updateStep(id, { progress: targetProgress });
      if (targetProgress >= 100) {
        await delay(300);
        updateStep(id, { status: 'done', progress: 100 });
      }
    },
    [updateStep],
  );

  const fetchHistory = useCallback(async () => {
    const fallback = getFallbackReports();
    const apiResult = await apiFetchSafe<ReportResponse[]>(`/projects/${projectId}/reports`);
    const apiReports = apiResult.ok ? apiResult.data : [];
    setHistory(mergeHistory(apiReports, fallback));
  }, [projectId]);

  useEffect(() => {
    void fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const completePipeline = useCallback(
    (activeReportId: string, filename: string, fallback: boolean) => {
      pipelineCompleteRef.current = true;
      stopPolling();
      setIsPipelineActive(false);
      setUsedFallback(fallback);

      updateStep('upload', { status: 'done', progress: 100 });
      updateStep('validate', { status: 'done', progress: 100 });
      updateStep('extract', { status: 'done', progress: 100 });
      updateStep('match', { status: 'done', progress: 100 });

      if (fallback) {
        persistFallbackProcessing(activeReportId, filename);
        setHistory((prev) => {
          const record = createFallbackReportRecord(activeReportId, filename);
          return mergeHistory(
            prev.filter((r): r is ReportResponse => !('isFallback' in r)),
            [record, ...getFallbackReports()],
          );
        });
      }

      setUploadStatus('done');
      notifyAppDataRefresh({ source: 'reports' });
      router.refresh();
      void fetchHistory();
    },
    [stopPolling, updateStep, router, fetchHistory],
  );

  const startStatusPolling = useCallback(
    (activeReportId: string, filename: string, fallback: boolean) => {
      stopPolling();
      pollingRef.current = setInterval(async () => {
        if (pipelineCompleteRef.current) return;
        const result = await apiFetchSafe<ReportResponse>(`/reports/${activeReportId}`);
        if (result.ok && isTerminalStatus(result.data.processing_status)) {
          completePipeline(activeReportId, filename, fallback);
        }
      }, 2000);
    },
    [stopPolling, completePipeline],
  );

  const runProcessingPipeline = useCallback(
    async (activeReportId: string, filename: string, forceFallback: boolean) => {
      pipelineCompleteRef.current = false;
      setIsPipelineActive(true);
      let fallback = forceFallback;

      setPipelineSteps([
        { id: 'upload', label: 'Uploading', filename, status: 'done', progress: 100 },
        { id: 'validate', label: 'Validating structure', status: 'done', progress: 100 },
        { id: 'extract', label: 'Extracting Events', status: 'in_progress', progress: 5 },
        { id: 'match', label: 'Matching to WBS', status: 'waiting', progress: 0 },
      ]);

      if (!fallback) {
        startStatusPolling(activeReportId, filename, false);
      }

      // --- Extract ---
      let extraction: ExtractionResultResponse;
      if (fallback) {
        await animateStep('extract', 100);
        extraction = buildFallbackExtraction(activeReportId);
      } else {
        await animateStep('extract', 40);
        const extractResult = await apiFetchSafe<ExtractionResultResponse>(
          `/reports/${activeReportId}/extract`,
          { method: 'POST' },
        );
        if (!extractResult.ok) {
          fallback = true;
          setContentWarning((prev) =>
            prev ??
            'Backend extraction failed — processing deterministic demo record (PIP-204-017 / HUMAN_REVIEW).',
          );
          await animateStep('extract', 100);
          extraction = buildFallbackExtraction(activeReportId);
        } else {
          extraction = extractResult.data;
          await animateStep('extract', 100);
          if (extraction.event_count === 0) {
            fallback = true;
            setContentWarning((prev) =>
              prev ??
              'No site events extracted from file — applying demo fallback record for pipeline completion.',
            );
            extraction = buildFallbackExtraction(activeReportId);
          }
        }
      }

      // --- Match ---
      updateStep('match', { status: 'in_progress', progress: 5 });
      const events = extraction.events ?? [];

      if (fallback || events.length === 0) {
        await animateStep('match', 100);
      } else {
        for (let i = 0; i < events.length; i++) {
          await apiFetchSafe(`/events/${events[i].event_id}/match`, { method: 'POST' });
          const progress = Math.max(10, Math.round(((i + 1) / events.length) * 100));
          updateStep('match', { status: 'in_progress', progress });
          await delay(200);
        }
        await animateStep('match', 100);

        const eventsMatched = events.length;
        if (eventsMatched === 0) {
          fallback = true;
        }
      }

      if (!pipelineCompleteRef.current) {
        completePipeline(activeReportId, filename, fallback);
      }
    },
    [animateStep, updateStep, startStatusPolling, completePipeline],
  );

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) {
      setSelectedFile(e.target.files[0]);
      setUploadStatus('idle');
      setReportId(null);
      setContentWarning(null);
      setUsedFallback(false);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setUploadStatus('uploading');
    setReportId(null);
    setContentWarning(null);
    setUsedFallback(false);
    pipelineCompleteRef.current = false;

    const fileText = await readFileAsText(selectedFile);
    const validation = looksLikeSiteReport(fileText, selectedFile.name);
    let forceFallback = !validation.isValid;

    if (!validation.isValid) {
      setContentWarning(
        validation.reason ??
          'File does not appear to contain construction site operational updates. A demo fallback record will be processed.',
      );
    }

    setPipelineSteps([
      { id: 'upload', label: 'Uploading', filename: selectedFile.name, status: 'in_progress', progress: 30 },
      { id: 'validate', label: 'Validating structure', status: 'waiting', progress: 0 },
      { id: 'extract', label: 'Extracting Events', status: 'waiting', progress: 0 },
      { id: 'match', label: 'Matching to WBS', status: 'waiting', progress: 0 },
    ]);
    setIsPipelineActive(true);

    let activeReportId: string;

    if (forceFallback) {
      await animateStep('upload', 100);
      await animateStep('validate', 100);
      activeReportId = generateFallbackReportId();
      setReportId(activeReportId);
      await runProcessingPipeline(activeReportId, selectedFile.name, true);
      return;
    }

    const uploadResult = await apiFetchSafe<ReportUploadResponse>('/reports/upload', {
      method: 'POST',
      body: (() => {
        const formData = new FormData();
        formData.append('file', selectedFile);
        formData.append('project_id', projectId);
        formData.append('report_date', new Date().toISOString().slice(0, 10));
        return formData;
      })(),
    });

    if (!uploadResult.ok) {
      forceFallback = true;
      setContentWarning(
        `Upload rejected by server (${uploadResult.error}). Processing deterministic demo fallback instead.`,
      );
      await animateStep('upload', 100);
      await animateStep('validate', 100);
      activeReportId = generateFallbackReportId();
    } else {
      await animateStep('upload', 100);
      await animateStep('validate', 100);
      activeReportId = uploadResult.data.report_id;
    }

    setReportId(activeReportId);
    await runProcessingPipeline(activeReportId, selectedFile.name, forceFallback);
  };

  const handleProcessVoice = () => {
    setIsProcessingVoice(true);
    setTimeout(() => {
      setIsProcessingVoice(false);
      setVoiceProcessed(true);
    }, 1500);
  };

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <div className="mb-8">
        <h2 className="text-[24px] font-semibold text-on-surface mb-2">Report Ingestion Hub</h2>
        <p className="text-[16px] text-on-surface-variant">Process field updates and operational reports via file or voice.</p>
      </div>

      {contentWarning && (
        <div
          role="alert"
          className="mb-6 flex items-start gap-3 rounded-xl border border-status-review/30 bg-status-review/10 px-4 py-3 text-[14px] text-on-surface"
        >
          <AlertTriangle size={18} className="text-status-review shrink-0 mt-0.5" />
          <p className="flex-1 leading-relaxed">{contentWarning}</p>
          <button
            type="button"
            onClick={() => setContentWarning(null)}
            className="text-on-surface-variant hover:text-on-surface shrink-0"
            aria-label="Dismiss alert"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {usedFallback && uploadStatus === 'done' && (
        <div className="mb-6 flex items-center gap-2 rounded-xl border border-status-completed/30 bg-status-completed/10 px-4 py-3 text-[13px] text-status-completed">
          <CheckCircle2 size={16} />
          Demo pipeline completed — WBS <span className="font-mono font-bold">PIP-204-017</span> routed to{' '}
          <span className="font-bold">HUMAN_REVIEW</span>.
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 flex flex-col gap-6">
          <div
            onClick={handleFileClick}
            className={`bg-surface-container-lowest border rounded-xl p-10 flex flex-col items-center justify-center border-dashed transition-colors cursor-pointer group h-[300px] ${selectedFile ? 'border-primary bg-primary/5' : 'border-surface-border hover:bg-surface-container-low'}`}
          >
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              onChange={handleFileChange}
              accept=".txt,.csv,.xlsx"
            />

            {selectedFile ? (
              <>
                <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-5 text-primary">
                  <CheckCircle2 size={32} />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-2">File Selected</h3>
                <p className="font-mono text-[14px] text-primary mb-6 text-center">{selectedFile.name}</p>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    void handleUpload();
                  }}
                  disabled={uploadStatus === 'uploading' || isPipelineActive}
                  className="px-6 py-2.5 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-70"
                >
                  {uploadStatus === 'uploading' && 'Uploading...'}
                  {uploadStatus === 'done' && `Done! ID: ${reportId}`}
                  {uploadStatus === 'error' && 'Failed - Retry'}
                  {uploadStatus === 'idle' && 'Upload & Process'}
                </button>
              </>
            ) : (
              <>
                <div className="w-16 h-16 bg-surface-container rounded-full flex items-center justify-center mb-5 group-hover:scale-105 transition-transform duration-300">
                  <UploadCloud size={32} className="text-primary" />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-2">Drag & Drop Reports</h3>
                <p className="text-[14px] text-on-surface-variant mb-6 text-center">Support for TXT, CSV, and XLSX WBS exports.</p>
                <button className="px-6 py-2.5 bg-surface-container-lowest text-primary text-[12px] font-bold rounded-lg hover:bg-surface-container-low transition-colors border border-surface-border shadow-sm">
                  Browse Files
                </button>
              </>
            )}
          </div>

          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-5">
              <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                <Mic className="text-primary" size={20} /> Local Voice Input
              </h3>
              <span className={`px-3 py-1 bg-surface-container-low rounded text-[11px] font-semibold tracking-wider uppercase flex items-center gap-2 border border-surface-border ${voiceProcessed ? 'text-status-completed' : 'text-on-surface-variant'}`}>
                {!voiceProcessed && <div className="w-2 h-2 rounded-full bg-status-conflict animate-pulse"></div>}
                {voiceProcessed ? 'Processed' : 'Recording'}
              </span>
            </div>

            <div className="h-20 bg-surface-container-low rounded-lg border border-surface-border mb-5 flex items-end justify-center gap-1.5 p-3 overflow-hidden">
              {[20, 70, 40, 90, 30, 80, 100, 60, 40, 85, 30, 70].map((h, i) => (
                <div
                  key={i}
                  className={`w-2 rounded-t-sm transition-all duration-500 ${voiceProcessed ? 'bg-status-completed' : 'bg-primary'}`}
                  style={{ height: voiceProcessed ? '10%' : `${h}%`, opacity: 0.8 }}
                ></div>
              ))}
            </div>

            <div className={`border rounded-lg p-5 mb-5 transition-colors ${voiceProcessed ? 'bg-status-completed/10 border-status-completed/20' : 'bg-surface-bright border-surface-border'}`}>
              <p className="font-mono text-[13px] text-on-surface leading-relaxed">
                &quot;Activity 24P201 foundation pour completed. Moving to curing phase. Next is steel erection on Monday...&quot;
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setVoiceProcessed(false)}
                className="px-5 py-2.5 border border-surface-border text-on-surface text-[12px] font-bold rounded-lg hover:bg-surface-container-high transition-colors bg-surface-container-lowest"
              >
                Reset
              </button>
              <button
                onClick={handleProcessVoice}
                disabled={isProcessingVoice || voiceProcessed}
                className={`px-5 py-2.5 text-[12px] font-bold rounded-lg transition-colors flex items-center gap-2 shadow-sm ${voiceProcessed ? 'bg-status-completed text-surface-container-lowest' : 'bg-primary text-on-primary hover:bg-primary/90'} disabled:opacity-70`}
              >
                {voiceProcessed ? <CheckCircle2 size={16} /> : <Sparkles size={16} />}
                {isProcessingVoice ? 'Processing...' : voiceProcessed ? 'Processed Successfully' : 'Process Spoken Update'}
              </button>
            </div>
          </div>
        </div>

        <div className="xl:col-span-1 flex flex-col gap-6">
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 shadow-sm">
            <h3 className="text-[18px] font-semibold text-on-surface mb-6">Active Pipeline</h3>
            {!isPipelineActive && uploadStatus === 'idle' ? (
              <p className="text-[14px] text-on-surface-variant">No active processing. Upload a report to begin.</p>
            ) : (
              <div className="space-y-5">
                {pipelineSteps.map((step) => (
                  <div key={step.id} className={step.status === 'waiting' && !isPipelineActive ? 'opacity-50' : undefined}>
                    <div className="flex justify-between text-[12px] font-bold mb-2">
                      <span className="text-on-surface">{stepLabel(step)}</span>
                      <span className={stepStatusClass(step)}>{stepStatusText(step)}</span>
                    </div>
                    <div className="w-full bg-surface-container rounded-full h-1.5">
                      <div
                        className={`h-1.5 rounded-full transition-all duration-500 ${stepBarClass(step)}`}
                        style={{ width: `${step.progress}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="bg-surface-container-lowest border border-surface-border rounded-xl flex-1 flex flex-col shadow-sm overflow-hidden">
            <div className="p-5 border-b border-surface-border">
              <h3 className="text-[18px] font-semibold text-on-surface">Ingestion History</h3>
            </div>
            <div className="overflow-y-auto flex-1">
              <table className="w-full text-left">
                <thead className="bg-surface-container-low text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider border-b border-surface-border">
                  <tr>
                    <th className="px-5 py-3">Filename</th>
                    <th className="px-5 py-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-surface-border">
                  {history.length === 0 ? (
                    <tr>
                      <td colSpan={2} className="px-5 py-6 text-[14px] text-on-surface-variant">
                        No reports uploaded yet.
                      </td>
                    </tr>
                  ) : (
                    history.map((row) => {
                      const rejected = row.processing_status === 'REJECTED' || row.processing_status === 'FAILED';
                      const isDemo = 'isFallback' in row && row.isFallback;
                      return (
                        <tr key={row.report_id} className="hover:bg-audit-previous transition-colors">
                          <td className="px-5 py-3">
                            <div className="font-mono text-[13px] text-on-surface">{row.filename}</div>
                            <div className="text-[12px] text-on-surface-variant mt-1">
                              {formatHistoryDate(row.created_at)}
                              {isDemo && ' · Demo fallback'}
                            </div>
                          </td>
                          <td className="px-5 py-3">
                            <span
                              className={`inline-flex items-center px-2 py-1 text-[11px] font-bold uppercase tracking-wide rounded-sm border ${
                                rejected
                                  ? 'bg-error-container text-error border-error/20'
                                  : 'bg-audit-new text-status-completed border-status-completed/20'
                              }`}
                            >
                              {formatHistoryStatus(row.processing_status)}
                            </span>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
