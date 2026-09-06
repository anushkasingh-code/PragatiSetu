'use client';


import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  Bot,
  X,
  Send,
  Mic,
  MicOff,
  Trash2,
  ChevronDown,
  ExternalLink,
  Loader2,
  Minimize2,
  Maximize2,
  HelpCircle,
  Activity,
  Layers,
  ArrowRight,
  Key,
  CheckCircle2,
  AlertCircle,
  Settings2,
} from 'lucide-react';
import Link from 'next/link';
import { apiFetchSafe } from '@/lib/api';
import { useProjectContext } from '@/lib/project-context';

interface ChatActivityItem {
  activity_id: string;
  description: string;
  wbs_id: string;
  percent_complete: number;
  status: string;
  similarity: number;
  discipline?: string;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  activities?: ChatActivityItem[];
  source?: string;
  model?: string;
}

// Removed hardcoded QUICK_PROMPTS array

// Helper to format simple markdown elements (bold, italic, code, headers, links, lists)
function renderFormattedText(text: string) {
  const lines = text.split('\n');
  return (
    <div className="space-y-1.5 text-[13px] leading-relaxed">
      {lines.map((line, idx) => {
        if (!line.trim()) return <div key={idx} className="h-1" />;

        // Headers
        if (line.startsWith('### ')) {
          return (
            <h4 key={idx} className="text-[14px] font-bold text-on-surface mt-2 mb-1">
              {line.replace('### ', '')}
            </h4>
          );
        }
        if (line.startsWith('## ')) {
          return (
            <h3 key={idx} className="text-[15px] font-bold text-on-surface mt-2.5 mb-1">
              {line.replace('## ', '')}
            </h3>
          );
        }

        // Bullet point
        if (line.startsWith('- ') || line.startsWith('* ')) {
          const bulletContent = line.slice(2);
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="text-primary font-bold mt-1 text-[10px]">•</span>
              <span className="flex-1">{renderInlineStyles(bulletContent)}</span>
            </div>
          );
        }

        // Numbered list
        const numMatch = line.match(/^(\d+)\.\s+(.*)/);
        if (numMatch) {
          return (
            <div key={idx} className="flex items-start gap-2 pl-2">
              <span className="font-mono text-primary text-[11px] font-bold mt-0.5">{numMatch[1]}.</span>
              <span className="flex-1">{renderInlineStyles(numMatch[2])}</span>
            </div>
          );
        }

        return <p key={idx}>{renderInlineStyles(line)}</p>;
      })}
    </div>
  );
}

function renderInlineStyles(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  while (remaining.length > 0) {
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);
    const boldMatch = remaining.match(/\*\*([^*]+)\*\*/);
    const codeMatch = remaining.match(/`([^`]+)`/);

    const matches = [
      linkMatch ? { type: 'link', match: linkMatch, index: linkMatch.index ?? 9999 } : null,
      boldMatch ? { type: 'bold', match: boldMatch, index: boldMatch.index ?? 9999 } : null,
      codeMatch ? { type: 'code', match: codeMatch, index: codeMatch.index ?? 9999 } : null,
    ].filter(Boolean) as { type: string; match: RegExpMatchArray; index: number }[];

    if (matches.length === 0) {
      parts.push(remaining);
      break;
    }

    matches.sort((a, b) => a.index - b.index);
    const first = matches[0];

    if (first.index > 0) {
      parts.push(remaining.substring(0, first.index));
    }

    if (first.type === 'link') {
      const isInternal = first.match[2].startsWith('/');
      if (isInternal) {
        parts.push(
          <Link
            key={keyIdx++}
            href={first.match[2]}
            className="text-primary hover:underline font-medium inline-flex items-center gap-0.5"
          >
            {first.match[1]}
          </Link>
        );
      } else {
        parts.push(
          <a
            key={keyIdx++}
            href={first.match[2]}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary hover:underline font-medium inline-flex items-center gap-0.5"
          >
            {first.match[1]}
            <ExternalLink size={11} className="inline ml-0.5 opacity-70" />
          </a>
        );
      }
    } else if (first.type === 'bold') {
      parts.push(
        <strong key={keyIdx++} className="font-semibold text-on-surface">
          {first.match[1]}
        </strong>
      );
    } else if (first.type === 'code') {
      parts.push(
        <code key={keyIdx++} className="px-1.5 py-0.5 bg-surface-container font-mono text-[11px] rounded text-primary border border-surface-border">
          {first.match[1]}
        </code>
      );
    }

    remaining = remaining.substring(first.index + first.match[0].length);
  }

  return <>{parts}</>;
}

export function AiChatDrawer() {
  const [isOpen, setIsOpen] = useState(false);
  const [isExpanded, setIsExpanded] = useState(false);
  const { selectedProjectId, setSelectedProjectId, projects } = useProjectContext();
  const currentProject = projects.find((p) => p.project_id === selectedProjectId);

  const quickPrompts = [
    `📊 Overall progress of ${currentProject ? currentProject.name : 'the project'}?`,
    '🔍 Find pipeline welding & spool activities',
    '⚠️ Are there any schedule conflicts or delays?',
    '🎙️ How do I log daily voice progress updates?',
  ];
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [engineSource, setEngineSource] = useState<'groq' | 'local_rag'>('local_rag');

  // Key Modal State
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [inputApiKey, setInputApiKey] = useState('');
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [keyFeedback, setKeyFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [keyStatus, setKeyStatus] = useState<{ configured: boolean; model: string; masked_key?: string | null }>({
    configured: false,
    model: 'PragatiSetu Local Dynamic Engine',
  });

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<any>(null);

  // Fetch Key Status from Backend
  const checkKeyStatus = useCallback(async () => {
    try {
      const res = await apiFetchSafe<{
        configured: boolean;
        source: string;
        model: string;
        masked_key?: string | null;
      }>('/ai/key-status');
      if (res.ok && res.data) {
        setKeyStatus(res.data);
        if (res.data.configured) {
          setEngineSource('groq');
        }
      }
    } catch {
      // fallback silently
    }
  }, []);

  useEffect(() => {
    checkKeyStatus();
  }, [checkKeyStatus, isOpen]);

  // Initialize SpeechRecognition
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SpeechRecognition) {
        setSpeechSupported(true);
        const recog = new SpeechRecognition();
        recog.continuous = false;
        recog.interimResults = false;
        recog.lang = 'en-US';

        recog.onresult = (event: any) => {
          const transcript = event.results[0][0].transcript;
          if (transcript) {
            setInputValue((prev) => (prev ? `${prev} ${transcript}` : transcript));
          }
          setIsListening(false);
        };

        recog.onerror = () => {
          setIsListening(false);
        };

        recog.onend = () => {
          setIsListening(false);
        };

        recognitionRef.current = recog;
      }
    }
  }, []);

  // Global listener to trigger open from Header / Sidebar
  useEffect(() => {
    const handleOpenEvent = () => {
      setIsOpen(true);
      setTimeout(() => inputRef.current?.focus(), 150);
    };
    window.addEventListener('open-pragatisetu-ai-chat', handleOpenEvent);
    return () => window.removeEventListener('open-pragatisetu-ai-chat', handleOpenEvent);
  }, []);

  // Auto scroll messages
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, scrollToBottom]);

  const toggleVoiceRecording = () => {
    if (!recognitionRef.current) return;
    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch {
        setIsListening(false);
      }
    }
  };

  const handleSaveKey = async () => {
    if (!inputApiKey.trim()) return;
    setIsSavingKey(true);
    setKeyFeedback(null);
    try {
      const res = await apiFetchSafe<{ status: string; message: string; configured: boolean; source: string }>('/ai/configure-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ groq_api_key: inputApiKey.trim() }),
      });
      if (res.ok && res.data && res.data.configured) {
        if (typeof window !== 'undefined') {
          localStorage.setItem('pragatisetu_groq_key', inputApiKey.trim());
        }
        setEngineSource('groq');
        setKeyFeedback({ type: 'success', text: 'Groq API Key activated! Llama-3.3-70B is now active.' });
        checkKeyStatus();
        setTimeout(() => {
          setIsKeyModalOpen(false);
          setKeyFeedback(null);
          setInputApiKey('');
        }, 1500);
      } else {
        setKeyFeedback({ type: 'error', text: 'Could not save API key. Please check key format.' });
      }
    } catch (err: any) {
      setKeyFeedback({ type: 'error', text: err?.message || 'Failed to configure API key.' });
    } finally {
      setIsSavingKey(false);
    }
  };

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend ?? inputValue).trim();
    if (!query || isLoading) return;

    setInputValue('');
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setIsLoading(true);

    try {
      const storedKey = typeof window !== 'undefined' ? localStorage.getItem('pragatisetu_groq_key') : null;

      const res = await apiFetchSafe<{
        reply: string;
        grounded_candidates: string[];
        activities: ChatActivityItem[];
        project_id: string;
        source: string;
        model?: string;
      }>('/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: selectedProjectId,
          messages: newHistory.map((m) => ({ role: m.role, content: m.content })),
          top_k: 4,
          api_key: storedKey || undefined,
        }),
      }, 30000);

      if (res.ok && res.data) {
        setEngineSource(res.data.source === 'groq' ? 'groq' : 'local_rag');
        const assistantMsg: ChatMessage = {
          id: `ai-${Date.now()}`,
          role: 'assistant',
          content: res.data.reply,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          activities: res.data.activities,
          source: res.data.source,
          model: res.data.model,
        };
        setMessages((prev) => [...prev, assistantMsg]);
      } else {
        const errorMsg: ChatMessage = {
          id: `ai-err-${Date.now()}`,
          role: 'assistant',
          content: 'Sorry, I encountered a temporary connection issue. Please verify the backend is running.',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: `ai-err-${Date.now()}`,
        role: 'assistant',
        content: 'Failed to reach AI Chat service. Please try again.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <>
      {/* ─── Floating Launcher Pill / Button ─────────────────────── */}
      {!isOpen && (
        <button
          onClick={() => {
            setIsOpen(true);
            setTimeout(() => inputRef.current?.focus(), 200);
          }}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 bg-primary text-on-primary rounded-full shadow-xl hover:shadow-2xl hover:scale-105 transition-all duration-200 cursor-pointer group border border-primary/30"
          title="Open PragatiSetu AI Copilot"
        >
          <div className="relative flex items-center justify-center">
            <Bot size={20} className="group-hover:rotate-12 transition-transform duration-300" />
            <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-primary animate-pulse"></span>
          </div>
          <span className="text-[13px] font-bold tracking-wide hidden sm:inline-block">
            AI Copilot
          </span>
        </button>
      )}

      {/* ─── Chat Window ─────────────────────────────────────────── */}
      {isOpen && (
        <div
          className={`fixed z-50 bg-surface-container-lowest border border-surface-border rounded-2xl shadow-2xl flex flex-col overflow-hidden transition-all duration-300 animate-fadeIn ${
            isExpanded
              ? 'inset-4 md:inset-10 w-auto h-auto'
              : 'bottom-4 right-4 w-[460px] max-w-[calc(100vw-2rem)] h-[620px] max-h-[calc(100vh-2rem)]'
          }`}
        >
          {/* Header */}
          <div className="px-4 py-3 bg-surface-container-low border-b border-surface-border flex items-center justify-between shrink-0">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-lg bg-primary/15 text-primary flex items-center justify-center shrink-0">
                <Bot size={18} />
              </div>
              <div>
                <div className="flex items-center gap-1.5">
                  <h3 className="text-[14px] font-bold text-on-surface leading-tight">
                    PragatiSetu Copilot
                  </h3>
                  <button
                    type="button"
                    onClick={() => setIsKeyModalOpen(true)}
                    className={`text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded border transition-colors cursor-pointer ${
                      engineSource === 'groq'
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20 hover:bg-emerald-500/20'
                        : 'bg-primary/10 text-primary border-primary/20 hover:bg-primary/20'
                    }`}
                    title="Click to configure Groq API Key"
                  >
                    {engineSource === 'groq' ? '⚡ Groq Llama' : '🧠 Dynamic RAG'}
                  </button>
                </div>
                <div className="flex items-center gap-1 text-[11px] text-on-surface-variant mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-status-completed inline-block"></span>
                  <span>Grounded in WBS Schedule</span>
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
              {/* API Key Modal Button */}
              <button
                type="button"
                onClick={() => setIsKeyModalOpen(true)}
                className={`p-1.5 rounded-lg border transition-colors cursor-pointer ${
                  engineSource === 'groq'
                    ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/20 hover:bg-emerald-500/20'
                    : 'bg-surface-container text-on-surface-variant hover:text-primary border-surface-border hover:bg-surface-container-high'
                }`}
                title="Configure Groq API Key"
              >
                <Key size={15} />
              </button>

              {/* Project Picker */}
              <select
                value={selectedProjectId || ''}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="text-[11px] font-bold bg-surface-container border border-surface-border rounded-md px-2 py-1 text-on-surface focus:outline-none cursor-pointer max-w-[120px] text-ellipsis"
                title="Active Project Context"
              >
                {!selectedProjectId && <option value="" disabled>No Project</option>}
                {projects.map(p => (
                  <option key={p.project_id} value={p.project_id}>
                    {p.name} ({p.project_id})
                  </option>
                ))}
              </select>

              {/* Clear */}
              {messages.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearChat}
                  className="p-1.5 text-on-surface-variant hover:text-status-conflict rounded-lg hover:bg-surface-container transition-colors cursor-pointer"
                  title="Clear Chat History"
                >
                  <Trash2 size={16} />
                </button>
              )}

              {/* Expand / Minimize */}
              <button
                type="button"
                onClick={() => setIsExpanded(!isExpanded)}
                className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container transition-colors cursor-pointer"
                title={isExpanded ? 'Restore window size' : 'Expand full screen'}
              >
                {isExpanded ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              </button>

              {/* Close */}
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-1.5 text-on-surface-variant hover:text-on-surface rounded-lg hover:bg-surface-container transition-colors cursor-pointer"
                title="Close AI Copilot"
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {/* Key Configuration Popover / Modal */}
          {isKeyModalOpen && (
            <div className="px-4 py-3 bg-surface-container-high border-b border-surface-border animate-fadeIn text-[12px]">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-1.5 font-bold text-on-surface">
                  <Key size={14} className="text-primary" />
                  <span>Groq API Key Configuration</span>
                </div>
                <button
                  type="button"
                  onClick={() => setIsKeyModalOpen(false)}
                  className="text-on-surface-variant hover:text-on-surface cursor-pointer"
                >
                  <X size={14} />
                </button>
              </div>

              <div className="mb-2 text-[11px] text-on-surface-variant">
                {keyStatus.configured ? (
                  <div className="flex items-center gap-1.5 text-emerald-600 font-medium">
                    <CheckCircle2 size={13} />
                    <span>Groq LLM Active: {keyStatus.masked_key || 'Configured'}</span>
                  </div>
                ) : (
                  <span>Enter your Groq API Key (`gsk_...`) to activate Llama-3.3-70B instant conversational reasoning.</span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="password"
                  placeholder="gsk_..."
                  value={inputApiKey}
                  onChange={(e) => setInputApiKey(e.target.value)}
                  className="flex-1 px-2.5 py-1.5 rounded-lg bg-surface border border-surface-border text-on-surface text-[12px] font-mono focus:outline-none focus:ring-1 focus:ring-primary"
                />
                <button
                  type="button"
                  onClick={handleSaveKey}
                  disabled={isSavingKey || !inputApiKey.trim()}
                  className="px-3 py-1.5 rounded-lg bg-primary text-on-primary font-bold text-[11px] hover:bg-primary/90 disabled:opacity-50 transition-colors cursor-pointer flex items-center gap-1 shrink-0"
                >
                  {isSavingKey ? <Loader2 size={13} className="animate-spin" /> : null}
                  <span>Activate</span>
                </button>
              </div>

              {keyFeedback && (
                <div
                  className={`mt-2 p-1.5 rounded text-[11px] flex items-center gap-1.5 ${
                    keyFeedback.type === 'success'
                      ? 'bg-emerald-500/10 text-emerald-600 border border-emerald-500/20'
                      : 'bg-status-conflict/10 text-status-conflict border border-status-conflict/20'
                  }`}
                >
                  {keyFeedback.type === 'success' ? <CheckCircle2 size={13} /> : <AlertCircle size={13} />}
                  <span>{keyFeedback.text}</span>
                </div>
              )}
            </div>
          )}

          {/* Conversation Feed */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-surface">
            {!selectedProjectId ? (
              <div className="h-full flex flex-col justify-center items-center text-center px-4 py-8 max-w-sm mx-auto">
                <div className="w-12 h-12 rounded-2xl bg-surface-container-high text-on-surface-variant flex items-center justify-center mb-3">
                  <Bot size={24} />
                </div>
                <h4 className="text-[16px] font-bold text-on-surface mb-1">
                  No Project Selected
                </h4>
                <p className="text-[12px] text-on-surface-variant leading-relaxed">
                  Please select a project to ask project-specific questions and analyze schedules.
                </p>
              </div>
            ) : messages.length === 0 ? (
              <div className="h-full flex flex-col justify-center items-center text-center px-4 py-8 max-w-sm mx-auto">
                <div className="w-12 h-12 rounded-2xl bg-primary/10 text-primary flex items-center justify-center mb-3">
                  <Bot size={24} />
                </div>
                <h4 className="text-[16px] font-bold text-on-surface mb-1">
                  How can I assist you today?
                </h4>
                <p className="text-[12px] text-on-surface-variant mb-5 leading-relaxed">
                  I can analyze your WBS schedule, find candidate activities, check physical progress actuals, and explain daily report events.
                </p>

                {/* Quick Prompts */}
                <div className="w-full space-y-1.5 text-left">
                  <p className="text-[10px] font-bold uppercase tracking-wider text-outline mb-1 px-1">
                    Suggested Queries
                  </p>
                  {quickPrompts.map((prompt, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => handleSendMessage(prompt)}
                      className="w-full text-left p-2.5 rounded-xl text-[12px] font-medium bg-surface-container-low hover:bg-surface-container border border-surface-border text-on-surface transition-colors cursor-pointer flex items-center justify-between group"
                    >
                      <span>{prompt}</span>
                      <ArrowRight size={13} className="text-outline group-hover:text-primary transition-transform group-hover:translate-x-0.5" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
                >
                  <div
                    className={`max-w-[90%] rounded-2xl p-3.5 text-[13px] ${
                      msg.role === 'user'
                        ? 'bg-primary text-on-primary rounded-br-xs shadow-xs'
                        : 'bg-surface-container-lowest border border-surface-border rounded-bl-xs shadow-xs text-on-surface'
                    }`}
                  >
                    {msg.role === 'assistant' ? (
                      <div>
                        {renderFormattedText(msg.content)}

                        {/* Grounded Activities Cards */}
                        {msg.activities && msg.activities.length > 0 && (
                          <div className="mt-3.5 pt-3 border-t border-surface-border space-y-2">
                            <div className="flex items-center gap-1.5 text-[11px] font-bold text-on-surface-variant uppercase tracking-wider">
                              <Layers size={13} className="text-primary" />
                              <span>Matched WBS Activities ({msg.activities.length})</span>
                            </div>
                            <div className="grid grid-cols-1 gap-2">
                              {msg.activities.map((act) => (
                                <Link
                                  key={act.activity_id}
                                  href={`/schedule?search=${encodeURIComponent(act.activity_id)}`}
                                  onClick={() => setIsOpen(false)}
                                  className="p-2.5 rounded-lg bg-surface-container-low hover:bg-surface-container border border-surface-border transition-colors block group"
                                >
                                  <div className="flex items-center justify-between mb-1">
                                    <span className="font-mono text-[12px] font-bold text-primary group-hover:underline">
                                      {act.activity_id}
                                    </span>
                                    <span
                                      className={`text-[9px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                                        act.status === 'COMPLETED'
                                          ? 'bg-status-completed/10 text-status-completed'
                                          : act.status === 'IN_PROGRESS'
                                          ? 'bg-emerald-500/10 text-emerald-600'
                                          : 'bg-surface-container-high text-outline'
                                      }`}
                                    >
                                      {act.status}
                                    </span>
                                  </div>
                                  <p className="text-[12px] font-medium text-on-surface line-clamp-1 mb-1.5">
                                    {act.description}
                                  </p>
                                  <div className="flex items-center justify-between text-[11px] text-on-surface-variant font-mono">
                                    <span>WBS: {act.wbs_id}</span>
                                    <span className="font-bold text-on-surface">{act.percent_complete}%</span>
                                  </div>
                                </Link>
                              ))}
                            </div>
                          </div>
                        )}

                        <div className="flex items-center justify-between mt-2 pt-1.5 border-t border-surface-border/50 text-[10px] text-on-surface-variant font-mono">
                          <span className="capitalize">{msg.source === 'groq' ? `⚡ Groq ${msg.model || ''}` : '🧠 Dynamic RAG'}</span>
                          <span>{msg.timestamp}</span>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <p className="whitespace-pre-wrap">{msg.content}</p>
                        <span className="text-[10px] text-on-primary/80 mt-1 block text-right font-mono">
                          {msg.timestamp}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}

            {isLoading && (
              <div className="flex items-start gap-2 max-w-[85%]">
                <div className="p-3.5 rounded-2xl rounded-bl-xs bg-surface-container-lowest border border-surface-border shadow-xs flex items-center gap-2">
                  <Loader2 size={16} className="animate-spin text-primary" />
                  <span className="text-[12px] text-on-surface-variant font-medium">
                    Analyzing project schedule & synthesizing response...
                  </span>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input Bar */}
          <div className="p-3 bg-surface-container-low border-t border-surface-border shrink-0">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="flex items-center gap-2"
            >
              <div className="relative flex-1 flex items-center">
                <input
                  ref={inputRef}
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={
                    isListening
                      ? 'Listening to voice input...'
                      : 'Ask PragatiSetu AI anything (e.g. status, delays, piping)...'
                  }
                  disabled={isLoading || !selectedProjectId}
                  className="w-full px-3.5 py-2.5 pr-10 text-[13px] rounded-xl bg-surface border border-surface-border text-on-surface placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary/40 transition-all disabled:opacity-50"
                />

                {/* Voice Input Button */}
                {speechSupported && (
                  <button
                    type="button"
                    onClick={toggleVoiceRecording}
                    className={`absolute right-2 p-1.5 rounded-lg transition-colors cursor-pointer ${
                      isListening
                        ? 'bg-status-conflict text-white animate-pulse'
                        : 'text-on-surface-variant hover:text-primary hover:bg-surface-container'
                    }`}
                    title={isListening ? 'Stop Listening' : 'Voice Input (Speech-to-Text)'}
                  >
                    {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                  </button>
                )}
              </div>

              <button
                type="submit"
                disabled={!inputValue.trim() || isLoading || !selectedProjectId}
                className="p-2.5 rounded-xl bg-primary text-on-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors cursor-pointer shadow-xs"
                title="Send Message"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>
      )}
    </>
  );
}
