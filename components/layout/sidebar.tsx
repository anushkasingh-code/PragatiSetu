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
  X
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useState } from 'react';

export function Sidebar({ isOpen, onClose }: { isOpen?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const [isNewProjectModalOpen, setIsNewProjectModalOpen] = useState(false);

  const navItems = [
    { name: 'Projects', href: '/projects', icon: Folder },
    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
    { name: 'Schedule', href: '/schedule', icon: Calendar },
    { name: 'Reports', href: '/reports', icon: BarChart2 },
    { name: 'Review Queue', href: '/review-queue', icon: ClipboardList },
    { name: 'Audit Trail', href: '/audit-trail', icon: History },
    { name: 'Settings', href: '#', icon: Settings },
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
            <h1 className="text-[20px] font-semibold text-primary leading-tight">Project Alpha</h1>
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
          <button onClick={() => {}} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors text-[14px] font-medium">
            <HelpCircle size={20} />
            Help Center
          </button>
          <button onClick={() => {}} className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-on-surface-variant hover:bg-surface-container-high transition-colors text-[14px] font-medium">
            <Headset size={20} />
            Contact Support
          </button>
        </div>
      </nav>

      {/* New Project Modal */}
      {isNewProjectModalOpen && (
        <div className="fixed inset-0 bg-on-surface/50 z-[60] flex items-center justify-center p-4 backdrop-blur-sm">
          <div className="bg-surface-container-lowest rounded-xl shadow-xl w-full max-w-md border border-surface-border overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-surface-border flex justify-between items-center bg-surface-bright">
              <h2 className="text-[18px] font-semibold text-on-surface">Create New Project</h2>
              <button onClick={() => setIsNewProjectModalOpen(false)} className="text-on-surface-variant hover:text-on-surface">
                <X size={20} />
              </button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wider">Project Name</label>
                <input type="text" placeholder="e.g. Project Beta" className="w-full px-3 py-2 bg-surface-container-low border border-surface-border rounded-lg text-[14px] focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="block text-[12px] font-bold text-on-surface-variant mb-1.5 uppercase tracking-wider">Project Code (WBS Prefix)</label>
                <input type="text" placeholder="e.g. 24P" className="w-full px-3 py-2 bg-surface-container-low border border-surface-border rounded-lg text-[14px] focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-surface-border flex justify-end gap-3 bg-surface-bright">
              <button onClick={() => setIsNewProjectModalOpen(false)} className="px-4 py-2 text-[13px] font-bold text-on-surface-variant hover:bg-surface-container-low rounded-lg transition-colors">
                Cancel
              </button>
              <button onClick={() => setIsNewProjectModalOpen(false)} className="px-4 py-2 text-[13px] font-bold bg-primary text-on-primary rounded-lg hover:bg-primary/90 transition-colors">
                Create Project
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

