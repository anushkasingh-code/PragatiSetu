'use client';

import React, { useState, useEffect } from 'react';
import {
  Sun,
  Moon,
  Laptop,
  Check,
  RotateCcw,
  MapPin,
  Clock,
  Globe,
  Bell,
  Wifi,
  HardHat,
  UserCheck,
  LogOut,
  SlidersHorizontal,
  Eye,
} from 'lucide-react';
import { useAuth } from '@/lib/auth-context';
import Image from 'next/image';

export interface WorkerPreferences {
  // Appearance
  theme: 'light' | 'dark' | 'system';
  density: 'comfortable' | 'compact';
  highContrast: boolean;
  textSize: 'standard' | 'large' | 'extra-large';

  // Site Station & Regional
  station: string;
  language: 'en' | 'hi' | 'as';
  dateFormat: 'DD/MM/YYYY' | 'DD-Mon-YYYY' | 'YYYY-MM-DD';
  shiftType: string;

  // Alerts
  shiftEndReminder: boolean;
  scheduleDelayAlerts: boolean;
  reviewStatusAlerts: boolean;
  soundAlerts: boolean;

  // Data & Offline
  offlineDrafts: boolean;
  dataSaverMode: boolean;
  autoSyncNetwork: boolean;
}

const DEFAULT_PREFERENCES: WorkerPreferences = {
  theme: 'light',
  density: 'comfortable',
  highContrast: false,
  textSize: 'standard',

  station: 'Pump Area · Section A',
  language: 'en',
  dateFormat: 'DD/MM/YYYY',
  shiftType: 'Day Shift (08:00 - 16:30 IST)',

  shiftEndReminder: true,
  scheduleDelayAlerts: true,
  reviewStatusAlerts: true,
  soundAlerts: false,

  offlineDrafts: true,
  dataSaverMode: false,
  autoSyncNetwork: true,
};

const PREFERENCES_STORAGE_KEY = 'pragatisetu:worker-preferences';

export default function SettingsPage() {
  const { user, openLoginModal, logout } = useAuth();
  const [prefs, setPrefs] = useState<WorkerPreferences>(DEFAULT_PREFERENCES);
  const [activeTab, setActiveTab] = useState<'appearance' | 'site' | 'notifications' | 'data' | 'account'>('appearance');
  const [savedIndicator, setSavedIndicator] = useState(false);

  // Apply theme to DOM
  const applyThemeToDOM = (theme: 'light' | 'dark' | 'system', highContrast: boolean) => {
    if (typeof window === 'undefined') return;
    const root = document.documentElement;

    if (theme === 'dark') {
      root.classList.add('dark');
    } else if (theme === 'light') {
      root.classList.remove('dark');
    } else {
      if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
        root.classList.add('dark');
      } else {
        root.classList.remove('dark');
      }
    }

    if (highContrast) {
      root.classList.add('high-contrast');
    } else {
      root.classList.remove('high-contrast');
    }
  };

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(PREFERENCES_STORAGE_KEY);
      if (stored) {
        const parsed = { ...DEFAULT_PREFERENCES, ...JSON.parse(stored) };
        setPrefs(parsed);
        applyThemeToDOM(parsed.theme, parsed.highContrast);
      }
    } catch {}
  }, []);

  // Instant Auto-Save Helper
  const updatePreference = <K extends keyof WorkerPreferences>(key: K, value: WorkerPreferences[K]) => {
    setPrefs((prev) => {
      const updated = { ...prev, [key]: value };
      try {
        localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(updated));
      } catch {}
      if (key === 'theme' || key === 'highContrast') {
        applyThemeToDOM(
          key === 'theme' ? (value as WorkerPreferences['theme']) : updated.theme,
          key === 'highContrast' ? (value as boolean) : updated.highContrast
        );
      }
      return updated;
    });

    setSavedIndicator(true);
    setTimeout(() => setSavedIndicator(false), 2000);
  };

  const handleReset = () => {
    if (confirm('Reset all settings to default values?')) {
      setPrefs(DEFAULT_PREFERENCES);
      try {
        localStorage.setItem(PREFERENCES_STORAGE_KEY, JSON.stringify(DEFAULT_PREFERENCES));
      } catch {}
      applyThemeToDOM(DEFAULT_PREFERENCES.theme, DEFAULT_PREFERENCES.highContrast);
      setSavedIndicator(true);
      setTimeout(() => setSavedIndicator(false), 2000);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto w-full space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-surface-border pb-6">
        <div>
          <h1 className="text-[24px] font-bold text-on-surface leading-tight">Settings &amp; Preferences</h1>
          <p className="text-[14px] text-on-surface-variant mt-1">
            Customize display themes, active station, and site notifications.
          </p>
        </div>

        {/* Live Auto-save indicator & Reset */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 text-[12px] font-medium">
            {savedIndicator ? (
              <span className="flex items-center gap-1 text-status-completed font-semibold transition-all">
                <Check size={14} /> Saved
              </span>
            ) : (
              <span className="text-on-surface-variant/70">Changes save automatically</span>
            )}
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-medium text-on-surface-variant hover:text-on-surface bg-surface-container-low hover:bg-surface-container-high border border-surface-border rounded-lg transition-colors cursor-pointer"
            title="Reset to default settings"
          >
            <RotateCcw size={13} />
            Reset defaults
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-surface-border gap-2 overflow-x-auto pb-px">
        {[
          { id: 'appearance', label: 'Appearance & Theme', icon: Sun },
          { id: 'site', label: 'Site Station & Shift', icon: MapPin },
          { id: 'notifications', label: 'Notifications & Alerts', icon: Bell },
          { id: 'data', label: 'Offline & Data Saver', icon: Wifi },
          { id: 'account', label: 'Worker Account', icon: HardHat },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as typeof activeTab)}
              className={`flex items-center gap-2 px-4 py-3 text-[13px] font-bold transition-all border-b-2 whitespace-nowrap cursor-pointer ${
                isActive
                  ? 'border-primary text-primary bg-primary/5 rounded-t-lg'
                  : 'border-transparent text-on-surface-variant hover:text-on-surface hover:bg-surface-container-low rounded-t-lg'
              }`}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: Appearance */}
      {activeTab === 'appearance' && (
        <div className="space-y-6">
          {/* Theme Selection */}
          <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-4">
            <div>
              <h3 className="text-[16px] font-semibold text-on-surface">Interface Theme</h3>
              <p className="text-[13px] text-on-surface-variant mt-0.5">
                Choose light mode for outdoor day shifts or dark mode for night shifts and low-light field stations.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-1">
              {[
                {
                  id: 'light',
                  title: 'Light Theme',
                  desc: 'Optimized for high ambient light & day shifts',
                  icon: Sun,
                },
                {
                  id: 'dark',
                  title: 'Dark Theme',
                  desc: 'Reduced eye strain for night shifts & control rooms',
                  icon: Moon,
                },
                {
                  id: 'system',
                  title: 'Match Device System',
                  desc: 'Automatically synchronizes with your device setting',
                  icon: Laptop,
                },
              ].map((t) => {
                const Icon = t.icon;
                const isSelected = prefs.theme === t.id;
                return (
                  <div
                    key={t.id}
                    onClick={() => updatePreference('theme', t.id as typeof prefs.theme)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all flex flex-col justify-between ${
                      isSelected
                        ? 'border-primary bg-primary/5 ring-1 ring-primary/40 shadow-sm'
                        : 'border-surface-border hover:border-primary/40 bg-surface-container-low/50'
                    }`}
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <div className={`p-2 rounded-lg ${isSelected ? 'bg-primary text-on-primary' : 'bg-surface-container-high text-on-surface'}`}>
                          <Icon size={18} />
                        </div>
                        {isSelected && (
                          <span className="text-[11px] font-bold text-primary flex items-center gap-1">
                            <Check size={14} /> Active
                          </span>
                        )}
                      </div>
                      <span className="font-bold text-[14px] text-on-surface block">{t.title}</span>
                      <span className="text-[12px] text-on-surface-variant block mt-1 leading-relaxed">{t.desc}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Density & Sunlight Visibility */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Table / Layout Density */}
            <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-4">
              <div>
                <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
                  <SlidersHorizontal size={18} className="text-primary" />
                  Table &amp; List Density
                </h3>
                <p className="text-[13px] text-on-surface-variant mt-0.5">
                  Adjust row spacing across reports and schedule views.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { id: 'comfortable', title: 'Comfortable', desc: 'Larger touch targets for site tablets' },
                  { id: 'compact', title: 'Compact', desc: 'More rows visible on supervisory screens' },
                ].map((d) => (
                  <button
                    key={d.id}
                    type="button"
                    onClick={() => updatePreference('density', d.id as typeof prefs.density)}
                    className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                      prefs.density === d.id
                        ? 'border-primary bg-primary/10 text-primary font-bold shadow-sm'
                        : 'border-surface-border bg-surface-container-low text-on-surface-variant hover:text-on-surface'
                    }`}
                  >
                    <span className="text-[13px] block font-semibold">{d.title}</span>
                    <span className="text-[11px] opacity-75 block mt-0.5">{d.desc}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Outdoor Sunlight High Contrast */}
            <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-4">
              <div>
                <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
                  <Eye size={18} className="text-primary" />
                  Outdoor High-Contrast Mode
                </h3>
                <p className="text-[13px] text-on-surface-variant mt-0.5">
                  Sharpens border contrast and text darkens to maintain visibility under bright outdoor sunlight.
                </p>
              </div>

              <div className="flex items-center justify-between p-3.5 rounded-xl bg-surface-container-low border border-surface-border">
                <span className="text-[13px] font-semibold text-on-surface">Enable High Contrast</span>
                <input
                  type="checkbox"
                  checked={prefs.highContrast}
                  onChange={(e) => updatePreference('highContrast', e.target.checked)}
                  className="w-5 h-5 accent-primary cursor-pointer"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: Site Station & Regional */}
      {activeTab === 'site' && (
        <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
              <MapPin size={18} className="text-primary" />
              Operational Sector &amp; Regional Standards
            </h3>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Set your active work area to automatically filter relevant activities and shift schedules.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Station / Sector */}
            <div className="space-y-1.5">
              <label className="text-[12px] font-bold text-on-surface-variant uppercase tracking-wider">
                Assigned Work Station / Pipeline Sector
              </label>
              <select
                value={prefs.station}
                onChange={(e) => updatePreference('station', e.target.value)}
                className="w-full bg-surface-container-low border border-surface-border rounded-lg px-3.5 py-2.5 text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary font-medium cursor-pointer"
              >
                <option value="Pump Area · Section A">Pump Area · Section A (Main Crude Pumps)</option>
                <option value="Pipe Rack Corridor · Section B">Pipe Rack Corridor · Section B</option>
                <option value="Compressor Station · Section C">Compressor Station · Section C</option>
                <option value="Tank Farm & Storage · Section D">Tank Farm &amp; Storage · Section D</option>
                <option value="Central Operations Control Cell">Central Operations Control Cell (HQ)</option>
              </select>
            </div>

            {/* Shift Type */}
            <div className="space-y-1.5">
              <label className="text-[12px] font-bold text-on-surface-variant uppercase tracking-wider">
                Shift Working Schedule
              </label>
              <select
                value={prefs.shiftType}
                onChange={(e) => updatePreference('shiftType', e.target.value)}
                className="w-full bg-surface-container-low border border-surface-border rounded-lg px-3.5 py-2.5 text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary font-medium cursor-pointer"
              >
                <option value="Day Shift (08:00 - 16:30 IST)">Day Shift (08:00 - 16:30 IST)</option>
                <option value="General Shift (09:00 - 18:00 IST)">General Shift (09:00 - 18:00 IST)</option>
                <option value="Night Shift (20:00 - 04:30 IST)">Night Shift (20:00 - 04:30 IST)</option>
              </select>
            </div>

            {/* Regional Language */}
            <div className="space-y-1.5">
              <label className="text-[12px] font-bold text-on-surface-variant uppercase tracking-wider flex items-center gap-1.5">
                <Globe size={14} /> Display Language
              </label>
              <select
                value={prefs.language}
                onChange={(e) => updatePreference('language', e.target.value as typeof prefs.language)}
                className="w-full bg-surface-container-low border border-surface-border rounded-lg px-3.5 py-2.5 text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary font-medium cursor-pointer"
              >
                <option value="en">English (Indian Standard)</option>
                <option value="hi">हिन्दी (Hindi)</option>
                <option value="as">অসমীয়া (Assamese - Duliajan Operations)</option>
              </select>
            </div>

            {/* Date Format */}
            <div className="space-y-1.5">
              <label className="text-[12px] font-bold text-on-surface-variant uppercase tracking-wider flex items-center gap-1.5">
                <Clock size={14} /> Date Display Format
              </label>
              <select
                value={prefs.dateFormat}
                onChange={(e) => updatePreference('dateFormat', e.target.value as typeof prefs.dateFormat)}
                className="w-full bg-surface-container-low border border-surface-border rounded-lg px-3.5 py-2.5 text-[14px] text-on-surface focus:outline-none focus:ring-2 focus:ring-primary font-medium cursor-pointer"
              >
                <option value="DD/MM/YYYY">DD/MM/YYYY (e.g. 05/09/2026)</option>
                <option value="DD-Mon-YYYY">DD-Mon-YYYY (e.g. 05-Sep-2026)</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD (e.g. 2026-09-05)</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* TAB 3: Notifications & Alerts */}
      {activeTab === 'notifications' && (
        <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
              <Bell size={18} className="text-primary" />
              Field Notifications &amp; Shift Reminders
            </h3>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Configure what notifications you receive during operational shifts.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">End-of-Shift DPR Reminder</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Sends a reminder alert 30 minutes before your shift closes to ensure your Daily Progress Report is logged.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.shiftEndReminder}
                onChange={(e) => updatePreference('shiftEndReminder', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>

            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Critical Schedule Delay Alerts</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Notifies you immediately when an activity in your sector encounters a delay on the Critical Path.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.scheduleDelayAlerts}
                onChange={(e) => updatePreference('scheduleDelayAlerts', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>

            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Review Queue Verification Updates</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Alerts you when a submitted progress item is approved or returned with comments by the project planner.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.reviewStatusAlerts}
                onChange={(e) => updatePreference('reviewStatusAlerts', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>

            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Sound Alert Tones</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Play an audio chime when an urgent task update or delay alert arrives.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.soundAlerts}
                onChange={(e) => updatePreference('soundAlerts', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: Offline & Data Saver */}
      {activeTab === 'data' && (
        <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
              <Wifi size={18} className="text-primary" />
              Offline Work &amp; Mobile Data Saver
            </h3>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Useful when inspecting remote pipeline valves or remote stations with weak cellular connectivity.
            </p>
          </div>

          <div className="space-y-4">
            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Auto-Save Offline Drafts</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Keeps your daily entries and notes saved in the browser so nothing is lost if your device loses signal.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.offlineDrafts}
                onChange={(e) => updatePreference('offlineDrafts', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>

            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Mobile Data Saver (Photo Compression)</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Compresses site photo evidence before upload to ensure quick submissions over 2G/3G connections.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.dataSaverMode}
                onChange={(e) => updatePreference('dataSaverMode', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>

            <div className="flex items-start justify-between gap-4 p-4 rounded-xl bg-surface-container-low border border-surface-border">
              <div>
                <span className="text-[14px] font-semibold text-on-surface block">Auto-Sync on Network Reconnection</span>
                <span className="text-[12px] text-on-surface-variant block mt-0.5">
                  Automatically uploads queued inspection logs as soon as your device reconnects to Wi-Fi or LTE.
                </span>
              </div>
              <input
                type="checkbox"
                checked={prefs.autoSyncNetwork}
                onChange={(e) => updatePreference('autoSyncNetwork', e.target.checked)}
                className="w-5 h-5 accent-primary cursor-pointer mt-1"
              />
            </div>
          </div>
        </div>
      )}

      {/* TAB 5: Worker Account */}
      {activeTab === 'account' && (
        <div className="bg-surface-container-lowest border border-surface-border rounded-xl p-6 space-y-6">
          <div>
            <h3 className="text-[16px] font-semibold text-on-surface flex items-center gap-2">
              <HardHat size={18} className="text-primary" />
              Active Worker Identity &amp; Profile
            </h3>
            <p className="text-[13px] text-on-surface-variant mt-0.5">
              Review your signed-in identity or switch worker roles for shift handover.
            </p>
          </div>

          {user ? (
            <div className="p-5 rounded-xl bg-surface-container-low border border-surface-border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-full border-2 border-primary/30 overflow-hidden relative bg-primary/10 flex items-center justify-center shrink-0">
                  {user.avatarUrl ? (
                    <Image
                      src={user.avatarUrl}
                      alt={user.name}
                      fill
                      referrerPolicy="no-referrer"
                      className="object-cover"
                    />
                  ) : (
                    <span className="text-[18px] font-bold text-primary">
                      {user.name.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                </div>
                <div>
                  <h4 className="text-[16px] font-bold text-on-surface">{user.name}</h4>
                  <span className="inline-block text-[11px] font-bold text-primary bg-primary/10 px-2 py-0.5 rounded border border-primary/20 mt-1 uppercase">
                    {user.role}
                  </span>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px] text-on-surface-variant mt-2 font-mono">
                    <span>Badge ID: {user.workerId}</span>
                    <span>&bull;</span>
                    <span>{user.email}</span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2.5 shrink-0 w-full sm:w-auto">
                <button
                  type="button"
                  onClick={openLoginModal}
                  className="flex-1 sm:flex-none px-3.5 py-2 text-[12px] font-bold rounded-lg bg-surface-container-lowest border border-surface-border hover:bg-surface-container-high text-on-surface transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <UserCheck size={15} />
                  Switch Worker
                </button>
                <button
                  type="button"
                  onClick={logout}
                  className="flex-1 sm:flex-none px-3.5 py-2 text-[12px] font-bold rounded-lg bg-status-conflict/10 text-status-conflict hover:bg-status-conflict/20 border border-status-conflict/20 transition-colors cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <LogOut size={15} />
                  Sign Out
                </button>
              </div>
            </div>
          ) : (
            <div className="p-6 rounded-xl bg-surface-container-low border border-surface-border text-center space-y-3">
              <p className="text-[14px] text-on-surface-variant">No active worker logged in.</p>
              <button
                type="button"
                onClick={openLoginModal}
                className="px-4 py-2 text-[13px] font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors cursor-pointer"
              >
                Sign In / Register Worker
              </button>
            </div>
          )}

          <div className="border-t border-surface-border pt-4">
            <div className="p-3.5 rounded-lg bg-primary/5 border border-primary/20 text-[12px] text-on-surface-variant">
              <p className="font-bold text-primary mb-0.5">Enterprise Access Security</p>
              <p>Session identity is authenticated against Oil India Limited project operational standards.</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
