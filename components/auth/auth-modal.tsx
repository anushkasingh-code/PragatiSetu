'use client';

import React, { useState } from 'react';
import { useAuth, DEMO_PERSONAS, WorkerRole } from '@/lib/auth-context';
import { X, Lock, Mail, User, HardHat, Building, CheckCircle2, ArrowRight } from 'lucide-react';

export function AuthModal() {
  const {
    isAuthModalOpen,
    authModalTab,
    closeAuthModal,
    login,
    signup,
    switchDemoPersona,
  } = useAuth();

  const [tab, setTab] = useState<'login' | 'signup'>(authModalTab);
  const [email, setEmail] = useState('ramesh.worker@oilindia.in');
  const [password, setPassword] = useState('password123');
  const [name, setName] = useState('');
  const [workerId, setWorkerId] = useState('');
  const [role, setRole] = useState<WorkerRole>('Site Supervisor');
  const [siteLocation, setSiteLocation] = useState('Pump Area · Sector A');
  const [submittedMessage, setSubmittedMessage] = useState<string | null>(null);

  // Sync internal tab with context
  React.useEffect(() => {
    setTab(authModalTab);
    setSubmittedMessage(null);
  }, [authModalTab, isAuthModalOpen]);

  if (!isAuthModalOpen) return null;

  const handleLoginSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(email, password, role);
  };

  const handleSignupSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const ok = signup(name, email, password, role, workerId);
    if (!ok) {
      setSubmittedMessage('Please enter a valid email address.');
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="bg-surface-container-lowest w-full max-w-lg rounded-2xl border border-surface-border shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        
        {/* Header */}
        <div className="px-6 py-5 border-b border-surface-border bg-surface-container-low flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-1.5 rounded-lg bg-primary/10 text-primary">
                <HardHat size={20} />
              </span>
              <h2 className="text-[20px] font-bold text-on-surface leading-snug">
                Worker Portal Authentication
              </h2>
            </div>
            <p className="text-[13px] text-on-surface-variant mt-1">
              PragatiSetu Site Operations · Smart India Hackathon 2026
            </p>
          </div>
          <button
            onClick={closeAuthModal}
            className="text-on-surface-variant hover:text-on-surface p-1 rounded-lg hover:bg-surface-container transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-surface-border bg-surface">
          <button
            type="button"
            onClick={() => {
              setTab('login');
              setSubmittedMessage(null);
            }}
            className={`flex-1 py-3 text-[14px] font-bold transition-all border-b-2 ${
              tab === 'login'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setTab('signup');
              setSubmittedMessage(null);
            }}
            className={`flex-1 py-3 text-[14px] font-bold transition-all border-b-2 ${
              tab === 'signup'
                ? 'border-primary text-primary bg-primary/5'
                : 'border-transparent text-on-surface-variant hover:text-on-surface'
            }`}
          >
            Register Worker
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          
          {/* Quick Demo Switcher Banner */}
          <div className="p-3.5 bg-primary/5 rounded-xl border border-primary/20 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-bold uppercase tracking-wider text-primary flex items-center gap-1.5">
                <Building size={14} /> Quick Demo Personas
              </span>
              <span className="text-[11px] text-on-surface-variant font-medium">1-Click Sign-in</span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {DEMO_PERSONAS.map((persona) => (
                <button
                  key={persona.id}
                  type="button"
                  onClick={() => {
                    switchDemoPersona(persona);
                    closeAuthModal();
                  }}
                  className="p-2 text-left rounded-lg bg-surface-container-lowest hover:bg-surface-container-high border border-surface-border transition-all flex flex-col justify-between group"
                >
                  <span className="text-[12px] font-bold text-on-surface group-hover:text-primary transition-colors truncate">
                    {persona.name}
                  </span>
                  <span className="text-[10px] font-semibold text-primary uppercase tracking-wide truncate">
                    {persona.role}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {tab === 'login' ? (
            /* Log In Form */
            <form onSubmit={handleLoginSubmit} className="space-y-4">
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                  Work Email / ID
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline" size={16} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="worker@oilindia.in"
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
              </div>

              <div>
                <div className="flex justify-between items-center mb-1.5">
                  <label className="block text-[12px] font-bold text-on-surface-variant uppercase tracking-wide">
                    Password
                  </label>
                  <span className="text-[11px] text-outline">Any password for demo</span>
                </div>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline" size={16} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                  Operational Role
                </label>
                <select
                  value={role}
                  onChange={(e) => setRole(e.target.value as WorkerRole)}
                  className="w-full px-3.5 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                >
                  <option value="Site Supervisor">Site Supervisor (DPR & Voice Reporting)</option>
                  <option value="Field Engineer">Field Engineer (Technical Inspections)</option>
                  <option value="Project Planner">Project Planner (Schedule Commits & WBS)</option>
                  <option value="Quality Inspector">Quality Inspector (Compliance & QA)</option>
                </select>
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-3 bg-primary text-on-primary rounded-xl text-[14px] font-bold hover:bg-primary/90 transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                Sign In to Site Portal <ArrowRight size={16} />
              </button>
            </form>
          ) : (
            /* Sign Up Form */
            <form onSubmit={handleSignupSubmit} className="space-y-4">
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                  Worker Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline" size={16} />
                  <input
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Anil Verma"
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                    Worker / Badge ID
                  </label>
                  <input
                    type="text"
                    value={workerId}
                    onChange={(e) => setWorkerId(e.target.value)}
                    placeholder="e.g. WKR-2026-99"
                    className="w-full px-3.5 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                    Designated Role
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value as WorkerRole)}
                    className="w-full px-3.5 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  >
                    <option value="Site Supervisor">Site Supervisor</option>
                    <option value="Field Engineer">Field Engineer</option>
                    <option value="Project Planner">Project Planner</option>
                    <option value="Quality Inspector">Quality Inspector</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                  Work Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline" size={16} />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="anil.verma@oilindia.in"
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wide">
                  Create Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-outline" size={16} />
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-10 pr-4 py-2.5 bg-surface-container-low border border-surface-border rounded-xl text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all"
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full mt-2 py-3 bg-primary text-on-primary rounded-xl text-[14px] font-bold hover:bg-primary/90 transition-all flex items-center justify-center gap-2 shadow-sm"
              >
                Create Worker Profile & Sign In <CheckCircle2 size={16} />
              </button>
            </form>
          )}

          {/* Database Notice */}
          <div className="p-3 bg-surface-container-low rounded-xl border border-surface-border text-[12px] text-on-surface-variant flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-status-completed shrink-0 animate-pulse"></span>
            <span>
              Connected to <strong>PostgreSQL / SQLite</strong>. For this demo, all credentials authenticate instantly.
            </span>
          </div>

        </div>
      </div>
    </div>
  );
}
