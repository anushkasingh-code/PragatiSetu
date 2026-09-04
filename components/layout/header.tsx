'use client';

import { Search, Bell, Grid, Menu, X } from 'lucide-react';
import Image from 'next/image';
import { useState } from 'react';

export function Header({ onMenuClick }: { onMenuClick?: () => void }) {
  const [showNotifications, setShowNotifications] = useState(false);

  return (
    <header className="bg-surface-container-lowest h-16 border-b border-surface-border flex justify-between items-center px-6 sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <div className="md:hidden flex items-center gap-2">
          <button onClick={onMenuClick} className="text-on-surface-variant cursor-pointer p-1">
            <Menu size={24} />
          </button>
          <span className="font-semibold text-[20px] text-primary">PragatiSetu</span>
        </div>
        
        <div className="hidden md:flex relative max-w-md w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors" size={18} />
          <input 
            type="text" 
            placeholder="Search operational data..." 
            className="w-full bg-surface-container-low border border-surface-border py-1.5 pl-10 pr-4 text-[14px] text-on-surface placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all rounded-lg"
          />
        </div>
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden lg:inline-block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider bg-surface-container-low px-3 py-1 rounded border border-surface-border">
          Project Alpha | Operational
        </span>
        
        <div className="flex items-center gap-2">
          <div className="relative">
            <button 
              onClick={() => setShowNotifications(!showNotifications)}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors relative ${showNotifications ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:bg-surface-container-low'}`}
            >
              <Bell size={20} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-status-conflict rounded-full border-2 border-surface-container-lowest"></span>
            </button>
            
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-50 overflow-hidden">
                <div className="px-4 py-3 border-b border-surface-border flex justify-between items-center bg-surface-bright">
                  <h3 className="font-semibold text-[14px] text-on-surface">Notifications</h3>
                  <button onClick={() => setShowNotifications(false)} className="text-on-surface-variant hover:text-on-surface"><X size={16} /></button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  <div className="px-4 py-3 border-b border-surface-border hover:bg-surface-container-low transition-colors cursor-pointer">
                    <p className="text-[13px] font-semibold text-on-surface">Schedule Conflict Detected</p>
                    <p className="text-[12px] text-on-surface-variant mt-1">Activity 24P201 is delayed by 3 days.</p>
                    <p className="text-[11px] text-primary font-medium mt-2">10 mins ago</p>
                  </div>
                  <div className="px-4 py-3 border-b border-surface-border hover:bg-surface-container-low transition-colors cursor-pointer">
                    <p className="text-[13px] font-semibold text-on-surface">New Field Report Extracted</p>
                    <p className="text-[12px] text-on-surface-variant mt-1">Supervisor J. Miller submitted a new DPR for L5-A-North.</p>
                    <p className="text-[11px] text-primary font-medium mt-2">1 hour ago</p>
                  </div>
                  <div className="px-4 py-3 hover:bg-surface-container-low transition-colors cursor-pointer">
                    <p className="text-[13px] font-semibold text-on-surface">Human Review Required</p>
                    <p className="text-[12px] text-on-surface-variant mt-1">AI match confidence at 68% for Rebar Installation.</p>
                    <p className="text-[11px] text-primary font-medium mt-2">2 hours ago</p>
                  </div>
                </div>
                <div className="px-4 py-2 border-t border-surface-border text-center bg-surface-bright hover:bg-surface-container-low transition-colors cursor-pointer">
                  <button className="text-[12px] font-bold text-primary w-full h-full">Mark all as read</button>
                </div>
              </div>
            )}
          </div>
          
          <button className="w-10 h-10 rounded-full flex items-center justify-center text-on-surface-variant hover:bg-surface-container-low transition-colors">
            <Grid size={20} />
          </button>
          <div className="w-8 h-8 rounded-full ml-2 border border-surface-border overflow-hidden cursor-pointer relative">
            <Image 
              src="https://picsum.photos/seed/user/100/100" 
              alt="User" 
              fill
              referrerPolicy="no-referrer"
              className="object-cover"
            />
          </div>
        </div>
      </div>
    </header>
  );
}
