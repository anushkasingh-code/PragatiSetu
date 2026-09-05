'use client';

import { notifyAppDataRefresh, useAppDataRefresh } from '@/lib/app-sync';
import { Suspense } from 'react';
import { formatLocalDateTime, parseServerDate } from '@/lib/date';
import { apiFetchSafe } from '@/lib/api';
import { delay } from '@/lib/report-fallback';
import { looksLikeSiteReport, readFileAsText } from '@/lib/report-validation';
import { getDeletedProjectCodes, isProjectDeleted } from '@/lib/projects';
import {
  UploadCloud,
  Mic,
  MicOff,
  CheckCircle2,
  AlertTriangle,
  X,
  Square,
  RotateCcw,
  Volume2,
  FileText,
  Loader2,
  Eye,
  Trash2,
} from 'lucide-react';
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

type HistoryRow = ReportResponse;

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
  return formatLocalDateTime(iso);
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



function ReportsIngestionHub() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeProject, setActiveProject] = useState<{ project_id: string; name: string; displayCode: string } | null>(null);

  const resolveActiveProject = useCallback(async () => {
    const deleted = getDeletedProjectCodes();
    const res = await apiFetchSafe<{ project_id: string; name: string; description?: string }[]>('/projects');
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

  useEffect(() => {
    void resolveActiveProject();
  }, [resolveActiveProject]);

  useAppDataRefresh(resolveActiveProject);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineCompleteRef = useRef(false);

  // Live Voice Input States & Audio Refs
  const [isRecording, setIsRecording] = useState(false);
  const [voiceTranscript, setVoiceTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const [waveformBars, setWaveformBars] = useState<number[]>([20, 35, 50, 75, 90, 60, 80, 65, 45, 60, 35, 20]);
  const [speechSupported, setSpeechSupported] = useState<boolean>(true);

  const recognitionRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [voiceProcessed, setVoiceProcessed] = useState(false);
  const [uploadStatus, setUploadStatus] = useState<'idle' | 'uploading' | 'done' | 'error'>('idle');
  const [reportId, setReportId] = useState<string | null>(null);
  const [pipelineSteps, setPipelineSteps] = useState<PipelineStep[]>(INITIAL_PIPELINE);
  const [history, setHistory] = useState<HistoryRow[]>([]);
  const [isPipelineActive, setIsPipelineActive] = useState(false);
  const [contentWarning, setContentWarning] = useState<string | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [selectedReportDetail, setSelectedReportDetail] = useState<HistoryRow | null>(null);

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
    if (!activeProject || isProjectDeleted(activeProject.project_id)) {
      setHistory([]);
      return;
    }
    const currentId = activeProject.project_id;
    const apiResult = await apiFetchSafe<ReportResponse[]>(`/projects/${encodeURIComponent(currentId)}/reports`);
    if (apiResult.ok && Array.isArray(apiResult.data)) {
      setHistory(apiResult.data);
    } else {
      setHistory([]);
    }
  }, [activeProject]);

  useEffect(() => {
    void fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const hasSpeech = !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);
      setSpeechSupported(hasSpeech);
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch {}
      }
      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioContextRef.current) {
        try { audioContextRef.current.close(); } catch {}
      }
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const completePipeline = useCallback(
    (activeReportId: string, filename: string) => {
      pipelineCompleteRef.current = true;
      stopPolling();
      setIsPipelineActive(false);

      updateStep('upload', { status: 'done', progress: 100 });
      updateStep('validate', { status: 'done', progress: 100 });
      updateStep('extract', { status: 'done', progress: 100 });
      updateStep('match', { status: 'done', progress: 100 });

      setUploadStatus('done');
      notifyAppDataRefresh({ source: 'reports' });
      router.refresh();
      void fetchHistory();
    },
    [stopPolling, updateStep, router, fetchHistory],
  );

  const startStatusPolling = useCallback(
    (activeReportId: string, filename: string) => {
      stopPolling();
      pollingRef.current = setInterval(async () => {
        if (pipelineCompleteRef.current) return;
        const result = await apiFetchSafe<ReportResponse>(`/reports/${activeReportId}`);
        if (result.ok && isTerminalStatus(result.data.processing_status)) {
          completePipeline(activeReportId, filename);
        }
      }, 2000);
    },
    [stopPolling, completePipeline],
  );

  const runProcessingPipeline = useCallback(
    async (activeReportId: string, filename: string) => {
      pipelineCompleteRef.current = false;
      setIsPipelineActive(true);

      setPipelineSteps([
        { id: 'upload', label: 'Uploading', filename, status: 'done', progress: 100 },
        { id: 'validate', label: 'Validating structure', status: 'done', progress: 100 },
        { id: 'extract', label: 'Extracting Events', status: 'in_progress', progress: 5 },
        { id: 'match', label: 'Matching to WBS', status: 'waiting', progress: 0 },
      ]);

      startStatusPolling(activeReportId, filename);

      // --- Extract ---
      await animateStep('extract', 40);
      const extractResult = await apiFetchSafe<ExtractionResultResponse>(
        `/reports/${activeReportId}/extract`,
        { method: 'POST' },
      );

      if (!extractResult.ok) {
        stopPolling();
        setIsPipelineActive(false);
        setUploadStatus('error');
        setContentWarning(
          `Backend extraction failed (${extractResult.error || 'Extraction error'}). The report remains in failed state. Please retry.`,
        );
        updateStep('extract', { status: 'waiting', progress: 0 });
        void fetchHistory();
        return;
      }

      const extraction = extractResult.data;
      await animateStep('extract', 100);

      if (!extraction.events || extraction.events.length === 0) {
        stopPolling();
        setIsPipelineActive(false);
        setUploadStatus('done');
        setContentWarning('No site events were identified in this report.');
        updateStep('match', { status: 'done', progress: 100 });
        void fetchHistory();
        notifyAppDataRefresh({ source: 'reports' });
        return;
      }

      // --- Match ---
      updateStep('match', { status: 'in_progress', progress: 5 });
      const events = extraction.events;

      for (let i = 0; i < events.length; i++) {
        const matchRes = await apiFetchSafe<{ decision?: string }>(`/events/${events[i].event_id}/match`, { method: 'POST' });
        if (matchRes.ok && matchRes.data.decision === 'AUTO_LINK') {
          await apiFetchSafe(`/events/${events[i].event_id}/apply`, { method: 'POST' });
        }
        const progress = Math.max(10, Math.round(((i + 1) / events.length) * 100));
        updateStep('match', { status: 'in_progress', progress });
        await delay(200);
      }
      await animateStep('match', 100);

      if (!pipelineCompleteRef.current) {
        completePipeline(activeReportId, filename);
      }
    },
    [animateStep, updateStep, startStatusPolling, stopPolling, completePipeline, fetchHistory],
  );

  const handleClearFile = (e?: React.MouseEvent) => {
    e?.stopPropagation();
    setSelectedFile(null);
    setUploadStatus('idle');
    setReportId(null);
    setContentWarning(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      setSelectedFile(files[0]);
      setUploadStatus('idle');
      setReportId(null);
      setContentWarning(null);
      setUsedFallback(false);
    }
  };

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

  const uploadAndProcessFile = async (fileToUpload: File) => {
    setUploadStatus('uploading');
    setReportId(null);
    setContentWarning(null);
    pipelineCompleteRef.current = false;

    const currentProj = activeProject || (await resolveActiveProject());
    if (!currentProj || isProjectDeleted(currentProj.project_id)) {
      setUploadStatus('error');
      setIsPipelineActive(false);
      setContentWarning(
        'No active project found. Please create or select an active project in the Projects Directory before uploading reports.',
      );
      return;
    }

    const fileText = await readFileAsText(fileToUpload);
    const validation = looksLikeSiteReport(fileText, fileToUpload.name);

    if (!validation.isValid) {
      setUploadStatus('error');
      setIsPipelineActive(false);
      setContentWarning(
        validation.reason ??
          'File does not appear to contain construction site operational updates. Please upload a valid site DPR report.',
      );
      return;
    }

    setPipelineSteps([
      { id: 'upload', label: 'Uploading', filename: fileToUpload.name, status: 'in_progress', progress: 30 },
      { id: 'validate', label: 'Validating structure', status: 'waiting', progress: 0 },
      { id: 'extract', label: 'Extracting Events', status: 'waiting', progress: 0 },
      { id: 'match', label: 'Matching to WBS', status: 'waiting', progress: 0 },
    ]);
    setIsPipelineActive(true);

    const uploadResult = await apiFetchSafe<ReportUploadResponse>('/reports/upload', {
      method: 'POST',
      body: (() => {
        const formData = new FormData();
        formData.append('file', fileToUpload);
        formData.append('project_id', currentProj.project_id);
        formData.append('report_date', new Date().toISOString().slice(0, 10));
        return formData;
      })(),
    });

    if (!uploadResult.ok) {
      setUploadStatus('error');
      setIsPipelineActive(false);
      setContentWarning(
        `Upload rejected by server: ${uploadResult.error || 'Server error uploading file'}. Please retry.`,
      );
      return;
    }

    await animateStep('upload', 100);
    await animateStep('validate', 100);
    const activeReportId = uploadResult.data.report_id;
    setReportId(activeReportId);
    await runProcessingPipeline(activeReportId, fileToUpload.name);
  };

  const handleUpload = () => {
    if (selectedFile) {
      void uploadAndProcessFile(selectedFile);
    }
  };

  const startVoiceRecording = async () => {
    setVoiceError(null);
    setVoiceProcessed(false);
    // Every recording session starts completely fresh
    setVoiceTranscript('');
    setInterimTranscript('');

    const windowObj = typeof window !== 'undefined' ? (window as any) : null;
    const SpeechRecognition = windowObj?.SpeechRecognition || windowObj?.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setVoiceError('Speech recognition is not supported in this browser. You can edit the text directly or load the sample update below.');
    } else {
      try {
        const rec = new SpeechRecognition();
        rec.continuous = true;
        rec.interimResults = true;
        rec.lang = 'en-IN';

        let sessionAccumulated = '';

        rec.onresult = (event: any) => {
          let interim = '';
          let final = '';
          for (let i = event.resultIndex; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
              final += event.results[i][0].transcript + ' ';
            } else {
              interim += event.results[i][0].transcript;
            }
          }
          if (final) {
            sessionAccumulated = (sessionAccumulated + ' ' + final).trim();
            setVoiceTranscript(sessionAccumulated);
          }
          setInterimTranscript(interim);
        };

        rec.onerror = (event: any) => {
          console.warn('Speech recognition notice:', event.error);
          if (event.error === 'not-allowed') {
            setVoiceError('Microphone permission was denied. Please allow microphone access in browser settings.');
          } else if (event.error !== 'no-speech') {
            setVoiceError(`Speech error: ${event.error}`);
          }
          stopVoiceRecording();
        };

        rec.onend = () => {
          setIsRecording(false);
          setInterimTranscript('');
        };

        recognitionRef.current = rec;
        rec.start();
        setIsRecording(true);
      } catch (err: any) {
        setVoiceError(`Could not start speech recognition: ${err?.message ?? 'error'}`);
      }
    }

    // Connect real audio stream for visualizer if possible
    try {
      if (typeof navigator !== 'undefined' && navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaStreamRef.current = stream;
        const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          audioContextRef.current = ctx;
          const source = ctx.createMediaStreamSource(stream);
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 64;
          source.connect(analyser);
          const dataArray = new Uint8Array(analyser.frequencyBinCount);

          const updateVisualizer = () => {
            analyser.getByteFrequencyData(dataArray);
            const bars = Array.from(dataArray.slice(0, 12)).map((val) =>
              Math.max(15, Math.min(100, Math.round((val / 255) * 100))),
            );
            setWaveformBars(bars);
            animFrameRef.current = requestAnimationFrame(updateVisualizer);
          };
          animFrameRef.current = requestAnimationFrame(updateVisualizer);
          return;
        }
      }
    } catch {
      // Audio context unavailable or mic permission rejected for visualizer
    }

    // Fallback dynamic wave bars while recording
    const interval = setInterval(() => {
      setWaveformBars(Array.from({ length: 12 }, () => Math.floor(25 + Math.random() * 65)));
    }, 120);
    animFrameRef.current = interval as any;
  };

  const stopVoiceRecording = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      try {
        audioContextRef.current.close();
      } catch {}
      audioContextRef.current = null;
    }
    if (animFrameRef.current) {
      if (typeof animFrameRef.current === 'number') {
        cancelAnimationFrame(animFrameRef.current);
        clearInterval(animFrameRef.current);
      }
      animFrameRef.current = null;
    }
    setIsRecording(false);
    setInterimTranscript('');
    setWaveformBars([20, 35, 50, 75, 90, 60, 80, 65, 45, 60, 35, 20]);
  };

  const handleResetVoice = () => {
    stopVoiceRecording();
    setVoiceTranscript('');
    setInterimTranscript('');
    setVoiceProcessed(false);
    setVoiceError(null);
  };

  const handleLoadSampleVoice = () => {
    setVoiceTranscript(
      'Activity 24P201 foundation pour completed. Moving to curing phase. Next is steel erection on Monday.',
    );
    setVoiceProcessed(false);
    setVoiceError(null);
  };

  const handleProcessVoice = async () => {
    if (!voiceTranscript.trim()) {
      setVoiceError('Please record or enter a spoken field update first.');
      return;
    }
    stopVoiceRecording();
    setIsProcessingVoice(true);
    setVoiceError(null);

    try {
      const now = new Date();
      const year = now.getFullYear();
      const month = String(now.getMonth() + 1).padStart(2, '0');
      const day = String(now.getDate()).padStart(2, '0');
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      const seconds = String(now.getSeconds()).padStart(2, '0');
      const filename = `voice_dpr_${year}${month}${day}_${hours}${minutes}${seconds}.txt`;
      const voiceFile = new File([voiceTranscript.trim()], filename, { type: 'text/plain' });

      await uploadAndProcessFile(voiceFile);
      setVoiceProcessed(true);
      // Clear transcript so next recording or typed update is completely fresh
      setVoiceTranscript('');
      setInterimTranscript('');
      setTimeout(() => {
        setVoiceProcessed(false);
      }, 3500);
    } catch {
      setVoiceError('Failed to process spoken update into the schedule pipeline.');
    } finally {
      setIsProcessingVoice(false);
    }
  };

  return (
    <div className="p-6 max-w-7xl mx-auto w-full">
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-0.5 rounded border border-primary/20">
            PragatiSetu Ingestion
          </span>
          <span className="text-[11px] font-mono text-on-surface-variant bg-surface-container-low px-2 py-0.5 rounded border border-surface-border font-semibold">
            {activeProject ? `${activeProject.name} (${activeProject.displayCode})` : 'No Active Project'}
          </span>
        </div>
        <h2 className="text-[24px] font-semibold text-on-surface mb-1">Report Ingestion Hub</h2>
        <p className="text-[14px] text-on-surface-variant">Process field updates and daily progress reports via file upload or hands-free voice.</p>
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



      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-2 flex flex-col gap-6">
          <div
            onClick={handleFileClick}
            onDragOver={handleDragOver}
            onDragEnter={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`bg-surface-container-lowest border rounded-xl p-10 flex flex-col items-center justify-center border-dashed transition-all cursor-pointer group h-[300px] ${
              isDraggingOver
                ? 'border-primary bg-primary/10 ring-2 ring-primary/40 scale-[1.01]'
                : selectedFile
                ? 'border-primary bg-primary/5'
                : 'border-surface-border hover:bg-surface-container-low'
            }`}
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
                <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-4 text-primary">
                  <CheckCircle2 size={32} />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-1">File Ready for Ingestion</h3>
                <p className="font-mono text-[14px] text-primary mb-1 text-center font-medium">{selectedFile.name}</p>
                <p className="text-[12px] text-on-surface-variant mb-5">
                  {(selectedFile.size / 1024).toFixed(1)} KB · Ready to match against WBS
                </p>
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      void handleUpload();
                    }}
                    disabled={uploadStatus === 'uploading' || isPipelineActive}
                    className="px-6 py-2.5 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-sm disabled:opacity-70 cursor-pointer"
                  >
                    {uploadStatus === 'uploading' && 'Uploading & Matching...'}
                    {uploadStatus === 'done' && 'Upload Complete'}
                    {uploadStatus === 'error' && 'Failed - Retry'}
                    {uploadStatus === 'idle' && 'Upload & Process'}
                  </button>

                  <button
                    type="button"
                    onClick={handleClearFile}
                    className="px-4 py-2.5 border border-surface-border bg-surface-container-lowest text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high text-[12px] font-bold rounded-lg transition-colors cursor-pointer"
                  >
                    {uploadStatus === 'done' ? 'Upload Another' : 'Cancel'}
                  </button>
                </div>
              </>
            ) : (
              <>
                <div className={`w-16 h-16 rounded-full flex items-center justify-center mb-5 transition-transform duration-300 ${
                  isDraggingOver ? 'bg-primary text-on-primary scale-110' : 'bg-surface-container text-primary group-hover:scale-105'
                }`}>
                  <UploadCloud size={32} />
                </div>
                <h3 className="text-[18px] font-semibold text-on-surface mb-2">
                  {isDraggingOver ? 'Drop Report File Here' : 'Drag & Drop Reports'}
                </h3>
                <p className="text-[14px] text-on-surface-variant mb-6 text-center">Support for TXT, CSV, and XLSX WBS exports.</p>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    fileInputRef.current?.click();
                  }}
                  className="px-6 py-2.5 bg-surface-container-lowest text-primary text-[12px] font-bold rounded-lg hover:bg-surface-container-low transition-colors border border-surface-border shadow-sm cursor-pointer"
                >
                  Browse Files
                </button>
              </>
            )}
          </div>

          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 shadow-sm">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-[18px] font-semibold text-on-surface flex items-center gap-2">
                <Mic className="text-primary" size={20} /> Local Voice Input
              </h3>
              <span
                className={`px-3 py-1 rounded text-[11px] font-bold tracking-wider uppercase flex items-center gap-2 border ${
                  isRecording
                    ? 'bg-red-500/10 text-red-600 border-red-500/30'
                    : voiceProcessed
                    ? 'bg-status-completed/10 text-status-completed border-status-completed/30'
                    : 'bg-surface-container-low text-on-surface-variant border-surface-border'
                }`}
              >
                {isRecording && <div className="w-2 h-2 rounded-full bg-red-500 animate-ping"></div>}
                {isRecording ? 'Listening...' : voiceProcessed ? 'Processed' : 'Mic Ready'}
              </span>
            </div>

            {voiceError && (
              <div className="mb-4 p-3 bg-amber-500/10 border border-amber-500/30 text-amber-800 dark:text-amber-300 rounded-lg text-[13px] flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle size={16} className="shrink-0 text-amber-600" />
                  <span>{voiceError}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setVoiceError(null)}
                  className="text-xs font-bold hover:underline cursor-pointer shrink-0"
                >
                  Dismiss
                </button>
              </div>
            )}

            {/* Audio Waveform Visualizer & Microphone Toggle */}
            <div className="relative bg-surface-container-low rounded-lg border border-surface-border mb-4 p-4 flex flex-col items-center justify-center gap-3 overflow-hidden">
              <div className="h-16 w-full flex items-end justify-center gap-1.5 px-4">
                {waveformBars.map((h, i) => (
                  <div
                    key={i}
                    className={`w-2.5 rounded-t-sm transition-all duration-150 ${
                      isRecording
                        ? 'bg-red-500'
                        : voiceProcessed
                        ? 'bg-status-completed'
                        : 'bg-primary/70'
                    }`}
                    style={{ height: `${h}%` }}
                  ></div>
                ))}
              </div>

              <div className="flex items-center gap-3 z-10">
                {!isRecording ? (
                  <button
                    type="button"
                    onClick={startVoiceRecording}
                    className="px-4 py-2 bg-primary text-on-primary text-[13px] font-bold rounded-lg hover:bg-primary/90 transition-all flex items-center gap-2 shadow-sm cursor-pointer"
                  >
                    <Mic size={16} /> Start Recording
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={stopVoiceRecording}
                    className="px-4 py-2 bg-red-600 text-white text-[13px] font-bold rounded-lg hover:bg-red-700 transition-all flex items-center gap-2 shadow-sm cursor-pointer animate-pulse"
                  >
                    <Square size={16} /> Stop Recording
                  </button>
                )}
                <span className="text-[12px] text-on-surface-variant font-medium">
                  {isRecording ? 'Speak clearly into your microphone...' : 'Click to speak or edit text directly'}
                </span>
              </div>
            </div>

            {/* Live / Editable Transcript Field */}
            <div className="mb-4">
              <div className="flex justify-between items-center mb-1.5">
                <label className="text-[12px] font-bold text-on-surface-variant uppercase tracking-wider">
                  Field Transcript (Live & Editable)
                </label>
                {interimTranscript && (
                  <span className="text-[11px] text-primary italic font-medium">
                    Listening: &quot;{interimTranscript}&quot;
                  </span>
                )}
              </div>
              <textarea
                rows={3}
                value={voiceTranscript}
                onChange={(e) => {
                  setVoiceTranscript(e.target.value);
                  setVoiceProcessed(false);
                }}
                placeholder="Spoken updates will appear here live as you speak. You can also type or edit directly..."
                className={`w-full p-3 font-mono text-[13px] text-on-surface bg-surface-bright rounded-lg border focus:outline-none focus:ring-2 focus:ring-primary transition-colors ${
                  voiceProcessed
                    ? 'bg-status-completed/10 border-status-completed/30 text-status-completed'
                    : 'border-surface-border'
                }`}
              />
            </div>

            {/* Actions Bar */}
            <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-surface-border">
              <button
                type="button"
                onClick={handleLoadSampleVoice}
                className="text-[12px] text-primary font-semibold hover:underline flex items-center gap-1.5 cursor-pointer"
              >
                <FileText size={14} /> Insert Sample DPR Update
              </button>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={handleResetVoice}
                  className="px-4 py-2 border border-surface-border text-on-surface text-[12px] font-bold rounded-lg hover:bg-surface-container-high transition-colors bg-surface-container-lowest cursor-pointer"
                >
                  Reset
                </button>
                <button
                  type="button"
                  onClick={handleProcessVoice}
                  disabled={isProcessingVoice || !voiceTranscript.trim() || isRecording}
                  className={`px-5 py-2.5 text-[12px] font-bold rounded-lg transition-colors flex items-center gap-2 shadow-sm ${
                    voiceProcessed
                      ? 'bg-status-completed text-surface-container-lowest'
                      : 'bg-primary text-on-primary hover:bg-primary/90'
                  } disabled:opacity-50 cursor-pointer`}
                >
                  {isProcessingVoice ? (
                    <>
                      <Loader2 size={16} className="animate-spin" /> Processing Spoken Update...
                    </>
                  ) : voiceProcessed ? (
                    <>
                      <CheckCircle2 size={16} /> Processed Successfully
                    </>
                  ) : (
                    <>
                      <FileText size={16} /> Process Spoken Update
                    </>
                  )}
                </button>
              </div>
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
                      return (
                        <tr
                          key={row.report_id}
                          onClick={() => setSelectedReportDetail(row)}
                          title="Click to inspect report details and events"
                          className="hover:bg-primary/5 transition-colors cursor-pointer group"
                        >
                          <td className="px-5 py-3">
                            <div className="font-mono text-[13px] text-on-surface group-hover:text-primary transition-colors flex items-center gap-1.5">
                              {row.filename}
                            </div>
                            <div className="text-[12px] text-on-surface-variant mt-1 flex items-center gap-1">
                              <span>{formatHistoryDate(row.created_at)}</span>
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

      {/* Interactive Report Inspection Modal */}
      {selectedReportDetail && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-50 p-4 animate-fadeIn"
          onClick={() => setSelectedReportDetail(null)}
        >
          <div
            className="bg-surface-container-lowest border border-surface-border rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-surface-border pb-4">
              <div>
                <span className="text-[11px] font-bold uppercase tracking-wider text-primary bg-primary/10 px-2.5 py-1 rounded">
                  Report Ingestion Record
                </span>
                <h3 className="text-[18px] font-semibold text-on-surface mt-2 font-mono">
                  {selectedReportDetail.filename}
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setSelectedReportDetail(null)}
                className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container"
              >
                <X size={20} />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 text-[13px]">
              <div className="bg-surface-container-low p-3 rounded-xl border border-surface-border">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1">
                  Report ID
                </span>
                <span className="font-mono text-on-surface font-semibold">
                  {selectedReportDetail.report_id}
                </span>
              </div>
              <div className="bg-surface-container-low p-3 rounded-xl border border-surface-border">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1">
                  Status
                </span>
                <span className="font-bold text-status-completed">
                  {formatHistoryStatus(selectedReportDetail.processing_status)}
                </span>
              </div>
              <div className="bg-surface-container-low p-3 rounded-xl border border-surface-border">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1">
                  Ingestion Time (Local)
                </span>
                <span className="text-on-surface font-medium">
                  {formatHistoryDate(selectedReportDetail.created_at)}
                </span>
              </div>
              <div className="bg-surface-container-low p-3 rounded-xl border border-surface-border">
                <span className="text-[11px] font-bold text-on-surface-variant uppercase tracking-wider block mb-1">
                  Project
                </span>
                <span className="font-bold text-on-surface">
                  {activeProject ? `${activeProject.name} (${activeProject.displayCode})` : 'Active Project'}
                </span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-surface-border">
              <button
                type="button"
                onClick={() => {
                  setSelectedReportDetail(null);
                  router.push(activeProject ? `/review-queue?project_id=${encodeURIComponent(activeProject.project_id)}` : '/review-queue');
                }}
                className="px-4 py-2 bg-surface-container-low hover:bg-surface-container-high border border-surface-border text-[12px] font-bold rounded-lg text-on-surface transition-colors cursor-pointer"
              >
                Open Review Queue
              </button>
              <button
                type="button"
                onClick={() => {
                  setSelectedReportDetail(null);
                  router.push(activeProject ? `/audit-trail?project_id=${encodeURIComponent(activeProject.project_id)}` : '/audit-trail');
                }}
                className="px-4 py-2 bg-primary text-on-primary text-[12px] font-bold rounded-lg hover:bg-primary/90 transition-colors shadow-sm cursor-pointer"
              >
                View in Audit Trail
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function ReportsPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center h-64 text-on-surface-variant">Loading...</div>}>
      <ReportsIngestionHub />
    </Suspense>
  );
}
