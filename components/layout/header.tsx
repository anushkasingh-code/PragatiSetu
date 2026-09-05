'use client';

import {
  Search,
  Bell,
  Grid,
  Menu,
  X,
  User,
  LogIn,
  LogOut,
  ChevronDown,
  HardHat,
  Settings,
  Folder,
  LayoutDashboard,
  Calendar,
  BarChart2,
  ClipboardList,
  History,
  Check,
  Bot,
} from 'lucide-react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useAuth, DEMO_PERSONAS } from '@/lib/auth-context';

export function Header({ onMenuClick }: { onMenuClick?: () => void }) {
  const router = useRouter();
  const [showNotifications, setShowNotifications] = useState(false);
  const [showAppLauncher, setShowAppLauncher] = useState(false);
  const [showProfileDropdown, setShowProfileDropdown] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const { user, openLoginModal, openSignupModal, logout, switchDemoPersona } = useAuth();

  const [notifications, setNotifications] = useState([
    {
      id: '1',
      title: 'Schedule Conflict Detected',
      message: 'Activity 24P201 is delayed by 3 days.',
      time: '10 mins ago',
      href: '/schedule',
      read: false,
    },
    {
      id: '2',
      title: 'New Field Report Extracted',
      message: 'Supervisor J. Miller submitted a new DPR for L5-A-North.',
      time: '1 hour ago',
      href: '/reports',
      read: false,
    },
    {
      id: '3',
      title: 'Human Review Required',
      message: 'AI match confidence at 68% for Rebar Installation.',
      time: '2 hours ago',
      href: '/review-queue',
      read: false,
    },
  ]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleNotificationClick = (item: typeof notifications[0]) => {
    setNotifications((prev) => prev.map((n) => (n.id === item.id ? { ...n, read: true } : n)));
    setShowNotifications(false);
    router.push(item.href);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      router.push(`/schedule?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  return (
    <header className="bg-surface-container-lowest h-16 border-b border-surface-border flex justify-between items-center px-6 sticky top-0 z-50 shrink-0">
      <div className="flex items-center gap-4 flex-1">
        <div className="md:hidden flex items-center gap-2">
          <button onClick={onMenuClick} className="text-on-surface-variant cursor-pointer p-1">
            <Menu size={24} />
          </button>
          <span className="font-semibold text-[20px] text-primary">PragatiSetu</span>
        </div>
        
        <form onSubmit={handleSearch} className="hidden md:flex relative max-w-md w-full group">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-outline group-focus-within:text-primary transition-colors" size={18} />
          <input 
            type="text" 
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search activities, WBS, or reports (Press Enter)..." 
            className="w-full bg-surface-container-low border border-surface-border py-1.5 pl-10 pr-4 text-[14px] text-on-surface placeholder:text-outline focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary transition-all rounded-lg"
          />
        </form>
      </div>

      <div className="flex items-center gap-4">
        <span className="hidden lg:inline-block text-[11px] font-semibold text-on-surface-variant uppercase tracking-wider bg-surface-container-low px-3 py-1 rounded border border-surface-border">
          PragatiSetu | Operational
        </span>
        
        <div className="flex items-center gap-2">
          {/* AI Copilot Trigger */}
          <button
            type="button"
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('open-pragatisetu-ai-chat'));
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 hover:bg-primary/15 border border-primary/20 text-primary text-[12px] font-bold transition-all cursor-pointer shadow-xs group"
            title="Open PragatiSetu AI Copilot"
          >
            <Bot size={16} className="group-hover:rotate-12 transition-transform duration-200" />
            <span className="hidden sm:inline">AI Copilot</span>
          </button>

          {/* Notifications */}
          <div className="relative">
            <button 
              onClick={() => {
                setShowNotifications(!showNotifications);
                setShowAppLauncher(false);
                setShowProfileDropdown(false);
              }}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors relative cursor-pointer ${showNotifications ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:bg-surface-container-low'}`}
              title="Site Notifications"
            >
              <Bell size={20} />
              {unreadCount > 0 && (
                <span className="absolute top-2 right-2 w-2 h-2 bg-status-conflict rounded-full border-2 border-surface-container-lowest"></span>
              )}
            </button>
            
            {showNotifications && (
              <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-50 overflow-hidden animate-fadeIn">
                <div className="px-4 py-3 border-b border-surface-border flex justify-between items-center bg-surface-bright">
                  <div className="flex items-center gap-2">
                    <h3 className="font-semibold text-[14px] text-on-surface">Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="text-[10px] font-bold bg-status-conflict text-white px-1.5 py-0.2 rounded-full">
                        {unreadCount}
                      </span>
                    )}
                  </div>
                  <button onClick={() => setShowNotifications(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                    <X size={16} />
                  </button>
                </div>
                <div className="max-h-96 overflow-y-auto">
                  {notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => handleNotificationClick(item)}
                      className={`px-4 py-3 border-b border-surface-border hover:bg-surface-container-low transition-colors cursor-pointer ${
                        !item.read ? 'bg-primary/5' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <p className="text-[13px] font-semibold text-on-surface">{item.title}</p>
                        {!item.read && <span className="w-1.5 h-1.5 rounded-full bg-primary"></span>}
                      </div>
                      <p className="text-[12px] text-on-surface-variant mt-1">{item.message}</p>
                      <p className="text-[11px] text-primary font-medium mt-2">{item.time}</p>
                    </div>
                  ))}
                </div>
                <div className="px-4 py-2.5 border-t border-surface-border text-center bg-surface-bright hover:bg-surface-container-low transition-colors">
                  <button
                    type="button"
                    onClick={handleMarkAllAsRead}
                    className="text-[12px] font-bold text-primary w-full h-full cursor-pointer hover:underline"
                  >
                    Mark all as read
                  </button>
                </div>
              </div>
            )}
          </div>
          
          {/* Quick App Launcher Grid */}
          <div className="relative">
            <button
              onClick={() => {
                setShowAppLauncher(!showAppLauncher);
                setShowNotifications(false);
                setShowProfileDropdown(false);
              }}
              className={`w-10 h-10 rounded-full flex items-center justify-center transition-colors cursor-pointer ${
                showAppLauncher ? 'bg-surface-container-high text-primary' : 'text-on-surface-variant hover:bg-surface-container-low'
              }`}
              title="Quick App Launcher"
            >
              <Grid size={20} />
            </button>

            {showAppLauncher && (
              <div className="absolute right-0 mt-2 w-72 bg-surface-container-lowest border border-surface-border rounded-xl shadow-lg z-50 p-3 animate-fadeIn">
                <div className="px-2 py-1.5 border-b border-surface-border mb-2 flex justify-between items-center">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant">PragatiSetu Modules</p>
                  <button onClick={() => setShowAppLauncher(false)} className="text-on-surface-variant hover:text-on-surface cursor-pointer">
                    <X size={14} />
                  </button>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { name: 'Dashboard', href: '/', icon: LayoutDashboard },
                    { name: 'Projects', href: '/projects', icon: Folder },
                    { name: 'Schedule', href: '/schedule', icon: Calendar },
                    { name: 'Reports', href: '/reports', icon: BarChart2 },
                    { name: 'Review Queue', href: '/review-queue', icon: ClipboardList },
                    { name: 'Audit Trail', href: '/audit-trail', icon: History },
                    { name: 'AI Copilot', href: '#ai-copilot', icon: Bot, isAi: true },
                  ].map((m) => {
                    const Icon = m.icon;
                    return (
                      <Link
                        key={m.name}
                        href={m.href}
                        onClick={(e) => {
                          setShowAppLauncher(false);
                          if ('isAi' in m && m.isAi) {
                            e.preventDefault();
                            if (typeof window !== 'undefined') {
                              window.dispatchEvent(new CustomEvent('open-pragatisetu-ai-chat'));
                            }
                          }
                        }}
                        className="p-2.5 rounded-lg hover:bg-surface-container-low border border-transparent hover:border-surface-border flex flex-col items-center justify-center gap-1.5 transition-all text-center group"
                      >
                        <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center group-hover:scale-105 transition-transform">
                          <Icon size={16} />
                        </div>
                        <span className="text-[11px] font-semibold text-on-surface truncate w-full">{m.name}</span>
                      </Link>
                    );
                  })}
                </div>
                <div className="mt-2 pt-2 border-t border-surface-border">
                  <Link
                    href="/settings"
                    onClick={() => setShowAppLauncher(false)}
                    className="w-full py-1.5 px-2 rounded-lg hover:bg-surface-container-low text-[12px] font-semibold text-on-surface-variant flex items-center justify-center gap-1.5 transition-colors"
                  >
                    <Settings size={14} /> Settings &amp; Preferences
                  </Link>
                </div>
              </div>
            )}
          </div>
          {/* User Profile / Login Button */}
          {user ? (
            <div className="relative ml-2">
              <button
                onClick={() => {
                  setShowProfileDropdown(!showProfileDropdown);
                  setShowNotifications(false);
                }}
                className="flex items-center gap-2 p-1 pl-1.5 pr-2.5 rounded-full hover:bg-surface-container-low border border-surface-border transition-all cursor-pointer group"
                title="Worker Profile & Persona Switcher"
              >
                <div className="w-8 h-8 rounded-full border border-primary/30 overflow-hidden relative bg-primary/10 flex items-center justify-center shrink-0">
                  {user.avatarUrl ? (
                    <Image
                      src={user.avatarUrl}
                      alt={user.name}
                      fill
                      referrerPolicy="no-referrer"
                      className="object-cover"
                    />
                  ) : (
                    <span className="text-[12px] font-bold text-primary">
                      {user.name.slice(0, 2).toUpperCase()}
                    </span>
                  )}
                  <span className="absolute bottom-0 right-0 w-2 h-2 bg-status-completed border border-surface-container-lowest rounded-full"></span>
                </div>
                
                <div className="hidden sm:flex flex-col text-left">
                  <span className="text-[12px] font-bold text-on-surface leading-tight group-hover:text-primary transition-colors">
                    {user.name}
                  </span>
                  <span className="text-[10px] font-semibold text-primary uppercase tracking-wide">
                    {user.role}
                  </span>
                </div>
                
                <ChevronDown size={14} className="text-outline group-hover:text-primary transition-transform duration-200" />
              </button>

              {/* Profile Dropdown Popover */}
              {showProfileDropdown && (
                <div className="absolute right-0 mt-2 w-80 bg-surface-container-lowest border border-surface-border rounded-2xl shadow-xl z-50 overflow-hidden">
                  {/* User Summary Card */}
                  <div className="p-4 bg-surface-container-low border-b border-surface-border flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl border border-primary/20 overflow-hidden relative shrink-0">
                      {user.avatarUrl && (
                        <Image src={user.avatarUrl} alt={user.name} fill className="object-cover" />
                      )}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <h4 className="text-[14px] font-bold text-on-surface truncate">{user.name}</h4>
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-status-completed/10 text-status-completed border border-status-completed/20 shrink-0">
                          LOGGED IN
                        </span>
                      </div>
                      <p className="text-[12px] text-on-surface-variant font-medium truncate">{user.role}</p>
                      <p className="text-[11px] text-outline font-mono mt-0.5 truncate">{user.email}</p>
                      <p className="text-[10px] text-primary font-mono font-semibold mt-1">Worker ID: {user.workerId}</p>
                    </div>
                  </div>

                  {/* Switch Demo Personas Section */}
                  <div className="p-3 border-b border-surface-border bg-surface">
                    <p className="text-[11px] font-bold uppercase tracking-wider text-on-surface-variant mb-2 px-1">
                      Demo Personas
                    </p>
                    <div className="space-y-1">
                      {DEMO_PERSONAS.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => {
                            switchDemoPersona(p);
                            setShowProfileDropdown(false);
                          }}
                          className={`w-full text-left px-2.5 py-2 rounded-lg text-[12px] flex items-center justify-between transition-colors ${
                            user.id === p.id
                              ? 'bg-primary/10 text-primary font-bold border border-primary/20'
                              : 'hover:bg-surface-container-high text-on-surface'
                          }`}
                        >
                          <div>
                            <span className="block font-medium">{p.name}</span>
                            <span className="block text-[10px] text-outline">{p.role}</span>
                          </div>
                          {user.id === p.id && (
                            <span className="text-[10px] font-bold text-primary">ACTIVE</span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="p-2 space-y-1">
                    <Link
                      href="/settings"
                      onClick={() => setShowProfileDropdown(false)}
                      className="w-full text-left px-3 py-2 text-[13px] font-medium text-on-surface hover:bg-surface-container-low rounded-lg transition-colors flex items-center gap-2"
                    >
                      <Settings size={16} className="text-outline" /> Settings &amp; Preferences
                    </Link>
                    <button
                      onClick={() => {
                        setShowProfileDropdown(false);
                        openLoginModal();
                      }}
                      className="w-full text-left px-3 py-2 text-[13px] font-medium text-on-surface hover:bg-surface-container-low rounded-lg transition-colors flex items-center gap-2"
                    >
                      <User size={16} className="text-outline" /> Switch Worker / Sign In
                    </button>
                    <button
                      onClick={() => {
                        setShowProfileDropdown(false);
                        logout();
                      }}
                      className="w-full text-left px-3 py-2 text-[13px] font-semibold text-status-conflict hover:bg-status-conflict/10 rounded-lg transition-colors flex items-center gap-2"
                    >
                      <LogOut size={16} /> Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center gap-2 ml-2">
              <button
                onClick={openLoginModal}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-on-primary text-[12px] font-bold hover:bg-primary/90 transition-all shadow-sm"
              >
                <LogIn size={15} /> Sign In
              </button>
              <button
                onClick={openSignupModal}
                className="hidden sm:inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-surface-container-low hover:bg-surface-container-high border border-surface-border text-on-surface text-[12px] font-bold transition-colors"
              >
                Register
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
