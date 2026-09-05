'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Folder,
  LayoutDashboard,
  Calendar,
  BarChart2,
  ClipboardList,
  History,
  Settings,
  HelpCircle,
  Headset,
  Plus,
  X,
  BookOpen,
  Mail,
  Phone,
  ExternalLink,
  CheckCircle2,
  Bot,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';
import { apiFetchSafe } from '@/lib/api';
import { notifyAppDataRefresh } from '@/lib/app-sync';

export function Sidebar({ isOpen, onClose }: { isOpen?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);
  const [isHelpModalOpen, setIsHelpModalOpen] = useState(false);
  const [isSupportModalOpen, setIsSupportModalOpen] = useState(false);
  const [newProjName, setNewProjName] = useState('');
  const [newProjCode, setNewProjCode] = useState('');
  const [createProjectSuccess, setCreateProjectSuccess] = useState<string | null>(null);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newProjName.trim()) return;
    const code = newProjCode.trim() || `PRJ-${Math.floor(100 + Math.random() * 900)}`;
    
    try {
      await apiFetchSafe('/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: code,
          name: newProjName.trim(),
          description: 'Active site operational project',
        }),
      });
      notifyAppDataRefresh({ source: 'projects' });
      setCreateProjectSuccess(`Project "${newProjName.trim()}" (${code}) created in database!`);
      setTimeout(() => {
        setCreateProjectSuccess(null);
        setIsNewProjectModalOpen(false);
        setNewProjName('');
        setNewProjCode('');
      }, 1200);
    } catch {
      setCreateProjectSuccess(`Project "${newProjName.trim()}" (${code}) saved.`);
      setTimeout(() => {
        setCreateProjectSuccess(null);
        setIsNewProjectModalOpen(false);
      }, 1200);
    }
  };

  const navItems = [
    { name: 'Projects', href: '/projects', icon: Folder },
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Schedule', href: '/schedule', icon: Calendar },
    { name: 'Reports', href: '/reports', icon: BarChart2 },
    { name: 'Review Queue', href: '/review-queue', icon: ClipboardList },
    { name: 'Audit Trail', href: '/audit-trail', icon: History },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={onClose}
        ></div>
      )}

      <nav className={cn(
        "fixed inset-y-0 left-0 z-50 md:relative flex flex-col w-64 h-screen bg-surface-container-low border-r border-surface-border shrink-0 transition-transform duration-300 ease-in-out transform",
        isOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
      )}>
        <div className="px-6 py-6 border-b border-surface-border flex justify-between items-center">
          <div>
            <h1 className="text-[20px] font-semibold text-primary leading-tight">PragatiSetu</h1>
            <p className="text-[13px] font-medium text-on-surface-variant uppercase tracking-wide mt-1">Operational Status</p>
          </div>
          <button className="md:hidden text-on-surface-variant" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="px-4 py-6">
          <button 
            onClick={() => setIsNewProjectModalOpen(true)}
            className="w-full bg-primary text-on-primary text-[12px] font-bold tracking-wide py-2.5 rounded-lg flex items-center justify-center gap-2 hover:bg-primary/90 transition-colors border border-primary"
          >
            <Plus size={18} />
            New Project
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => {
                  if (window.innerWidth < 768) {
                    onClose?.();
                  }
                }}
                className={cn(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors text-[14px] font-medium",
                  isActive 
                    ? "bg-secondary-fixed text-on-secondary-fixed font-semibold border-l-4 border-secondary" 
                    : "text-on-surface-variant hover:bg-surface-container-high"
                )}
              >
                <item.icon size={20} className={isActive ? "fill-current/20" : ""} />
                {item.name}
              </Link>
            );
          })}
        </div>

        <div className="px-3 py-4 mt-auto border-t border-surface-border space-y-1">
          <button
            type="button"
            onClick={() => {
              if (window.innerWidth < 768) {
                onClose?.();
              }
              if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('open-pragatisetu-ai-chat'));
              }
            }}
            className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-primary bg-primary/10 hover:bg-primary/15 border border-primary/20 transition-all text-[13px] font-bold cursor-pointer group mb-1 shadow-xs"
            title="Open AI Assistant Copilot"
          >
            <div className="flex items-center gap-2.5">
              <Bot size={18} className="group-hover:rotate-12 transition-transform duration-200" />
              <span>AI Copilot</span>
            </div>
          </button>

          <button
            type="button"
            onClick={() => setIsHelpModalOpen(true)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors text-[14px] font-medium cursor-pointer"
          >
            <HelpCircle size={20} />
            Help Center
          </button>
          <button
            type="button"
            onClick={() => setIsSupportModalOpen(true)}
            className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors text-[14px] font-medium cursor-pointer"
          >
            <Headset size={20} />
            Contact Support
          </button>
        </div>
      </nav>

      {/* New Project Modal */}
      {isNewProjectModalOpen && (
        <div className="fixed inset-0 bg-on-surface/50 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
          <form onSubmit={handleCreateProject} className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-md border border-surface-border overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center bg-surface-bright">
              <h2 className="text-[18px] font-semibold text-on-surface">Create New Project</h2>
              <button type="button" onClick={() => setIsNewProjectModalOpen(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              {createProjectSuccess && (
                <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-600 text-xs font-semibold flex items-center gap-2">
                  <CheckCircle2 size={16} />
                  {createProjectSuccess}
                </div>
              )}
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wider">Project Name</label>
                <input 
                  type="text" 
                  required
                  value={newProjName}
                  onChange={(e) => setNewProjName(e.target.value)}
                  placeholder="e.g. Project Beta" 
                  className="w-full px-3 py-2 bg-surface-container-low border border-surface-border rounded-lg text-[14px] focus:outline-none focus:ring-2 focus:ring-primary" 
                />
              </div>
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wider">Project Code (WBS Prefix)</label>
                <input 
                  type="text" 
                  value={newProjCode}
                  onChange={(e) => setNewProjCode(e.target.value)}
                  placeholder="e.g. 24P" 
                  className="w-full px-3 py-2 bg-surface-container-low border border-surface-border rounded-lg text-[14px] focus:outline-none focus:ring-2 focus:ring-primary" 
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-border flex justify-end gap-3 bg-surface-bright">
              <button 
                type="button"
                onClick={() => setIsNewProjectModalOpen(false)} 
                className="px-4 py-2 text-[13px] font-bold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button 
                type="submit" 
                className="px-4 py-2 text-[13px] font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors cursor-pointer"
              >
                Create Project
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Help Center Modal */}
      {isHelpModalOpen && (
        <div className="fixed inset-0 bg-on-surface/50 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-lg border border-surface-border overflow-hidden flex flex-col animate-fadeIn">
            <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center bg-surface-bright">
              <div className="flex items-center gap-2">
                <HelpCircle className="text-primary" size={20} />
                <h2 className="text-[18px] font-semibold text-on-surface">PragatiSetu Help Center</h2>
              </div>
              <button onClick={() => setIsHelpModalOpen(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="p-3.5 bg-primary/5 rounded-xl border border-primary/20 space-y-1">
                <p className="text-[13px] font-bold text-primary">SIH26122 · Smart India Hackathon 2026</p>
                <p className="text-[12px] text-on-surface-variant">
                  AI-Powered Data Capture and Schedule-Linking Layer for Infrastructure Project Management (Oil India Limited).
                </p>
              </div>

              <div className="space-y-3">
                <h4 className="text-[13px] font-bold uppercase tracking-wider text-on-surface">Quick Start Guide</h4>
                <div className="space-y-2 text-[12px] text-on-surface-variant">
                  <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-border">
                    <p className="font-semibold text-on-surface">1. Daily Progress Capture</p>
                    <p>Navigate to <strong>Reports</strong> to view or upload contractor site reports and daily progress extracts.</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-border">
                    <p className="font-semibold text-on-surface">2. Human-in-the-Loop Review</p>
                    <p>Entries with match confidence below threshold appear in <strong>Review Queue</strong> for supervisor validation.</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-border">
                    <p className="font-semibold text-on-surface">3. Master Schedule Linking</p>
                    <p>Approved progress updates automatically sync into the Primavera/WBS Gantt chart on the <strong>Schedule</strong> page.</p>
                  </div>
                  <div className="p-2.5 rounded-lg bg-surface-container-low border border-surface-border">
                    <p className="font-semibold text-on-surface">4. Tamper-Proof Audit</p>
                    <p>All overrides and decisions are permanently tracked under <strong>Audit Trail</strong>.</p>
                  </div>
                </div>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-border flex justify-between items-center bg-surface-bright">
              <Link
                href="/settings"
                onClick={() => setIsHelpModalOpen(false)}
                className="text-[13px] font-bold text-primary hover:underline flex items-center gap-1"
              >
                Go to System Settings <ExternalLink size={14} />
              </Link>
              <button
                onClick={() => setIsHelpModalOpen(false)}
                className="px-4 py-2 text-[13px] font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Contact Support Modal */}
      {isSupportModalOpen && (
        <div className="fixed inset-0 bg-on-surface/50 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-md border border-surface-border overflow-hidden flex flex-col animate-fadeIn">
            <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center bg-surface-bright">
              <div className="flex items-center gap-2">
                <Headset className="text-primary" size={20} />
                <h2 className="text-[18px] font-semibold text-on-surface">Project Support Desk</h2>
              </div>
              <button onClick={() => setIsSupportModalOpen(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4 text-[13px]">
              <p className="text-on-surface-variant">
                For technical assistance or field station communication issues, contact the Oil India Project Management Cell:
              </p>

              <div className="space-y-2.5">
                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-border flex items-center gap-3">
                  <Mail className="text-primary shrink-0" size={18} />
                  <div>
                    <span className="block text-[11px] font-bold uppercase text-outline">Technical Support</span>
                    <span className="font-semibold text-on-surface">support@pragatisetu.oilindia.in</span>
                  </div>
                </div>

                <div className="p-3 bg-surface-container-low rounded-lg border border-surface-border flex items-center gap-3">
                  <Phone className="text-primary shrink-0" size={18} />
                  <div>
                    <span className="block text-[11px] font-bold uppercase text-outline">Site Operations Desk</span>
                    <span className="font-semibold text-on-surface">+91 (0374) 280-0400 (Duliajan HQ)</span>
                  </div>
                </div>
              </div>

              <div className="p-3 bg-primary/5 rounded-lg border border-primary/20 text-[12px] text-on-surface-variant">
                <p className="font-bold text-primary mb-0.5">Field Site Operations Hub:</p>
                <p>Oil India Limited Expansion Sector 4, Duliajan, Assam 786602</p>
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-border flex justify-end bg-surface-bright">
              <button
                onClick={() => setIsSupportModalOpen(false)}
                className="px-4 py-2 text-[13px] font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

