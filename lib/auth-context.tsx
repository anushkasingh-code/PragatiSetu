'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

export type WorkerRole =
  | 'Site Supervisor'
  | 'Field Engineer'
  | 'Project Planner'
  | 'Quality Inspector';

export interface AuthUser {
  id: string;
  name: string;
  email: string;
  role: WorkerRole;
  workerId: string;
  siteLocation: string;
  avatarUrl?: string;
  isDemoPersona?: boolean;
}

/**
 * CLIENT-ONLY DEMO PERSONAS FOR SIH PROTOTYPE SIMULATION ONLY.
 * These personas provide quick role-switching in the prototype frontend.
 * They are strictly isolated and MUST NOT be mistaken for real backend enterprise authentication (e.g. OAuth / SSO).
 */
export const DEMO_PERSONAS: AuthUser[] = [
  {
    id: 'USR-001',
    name: 'Ramesh Sharma',
    email: 'ramesh.worker@oilindia.in',
    role: 'Site Supervisor',
    workerId: 'WKR-OIL-2026',
    siteLocation: 'Pump Area · Section A',
    avatarUrl: 'https://picsum.photos/seed/ramesh/100/100',
    isDemoPersona: true,
  },
  {
    id: 'USR-002',
    name: 'Priya Patel',
    email: 'priya.engineer@oilindia.in',
    role: 'Field Engineer',
    workerId: 'ENG-OIL-4019',
    siteLocation: 'Pipe Rack Corridor · Section B',
    avatarUrl: 'https://picsum.photos/seed/priya/100/100',
    isDemoPersona: true,
  },
  {
    id: 'USR-003',
    name: 'J. Miller',
    email: 'j.miller@pragatisetu.gov.in',
    role: 'Project Planner',
    workerId: 'PLN-HQ-104',
    siteLocation: 'Central Planning & Scheduling Cell',
    avatarUrl: 'https://picsum.photos/seed/miller/100/100',
    isDemoPersona: true,
  },
];

interface AuthContextType {
  user: AuthUser | null;
  isAuthModalOpen: boolean;
  authModalTab: 'login' | 'signup';
  openLoginModal: () => void;
  openSignupModal: () => void;
  closeAuthModal: () => void;
  login: (email: string, password?: string, role?: WorkerRole) => boolean;
  signup: (name: string, email: string, password?: string, role?: WorkerRole, workerId?: string) => boolean;
  switchDemoPersona: (persona: AuthUser) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const AUTH_STORAGE_KEY = 'pragatisetu:demo-auth-user';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [authModalTab, setAuthModalTab] = useState<'login' | 'signup'>('login');
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        setUser(JSON.parse(stored));
      } else {
        // Default to the first demo worker
        setUser(DEMO_PERSONAS[0]);
        localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(DEMO_PERSONAS[0]));
      }
    } catch {
      setUser(DEMO_PERSONAS[0]);
    }
  }, []);

  const openLoginModal = () => {
    setAuthModalTab('login');
    setIsAuthModalOpen(true);
  };

  const openSignupModal = () => {
    setAuthModalTab('signup');
    setIsAuthModalOpen(true);
  };

  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  const login = (email: string, _password = '', role: WorkerRole = 'Site Supervisor') => {
    const matched = DEMO_PERSONAS.find((p) => p.email.toLowerCase() === email.toLowerCase());
    const randomId = Math.random().toString(36).substring(2, 7);
    const cleanName = email.split('@')[0].replace('.', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    const loggedInUser: AuthUser = matched ?? {
      id: `USR-${randomId}`,
      name: cleanName,
      email,
      role,
      workerId: `WKR-${randomId.toUpperCase()}`,
      siteLocation: 'Site Execution Sector 4',
      avatarUrl: `https://picsum.photos/seed/${encodeURIComponent(cleanName)}/100/100`,
    };

    setUser(loggedInUser);
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(loggedInUser));
    } catch {}
    setIsAuthModalOpen(false);
    return true;
  };

  const signup = (
    name: string,
    email: string,
    _password = '',
    role: WorkerRole = 'Site Supervisor',
    workerId?: string
  ) => {
    const cleanEmail = (email || '').trim();
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!cleanEmail || !emailRegex.test(cleanEmail)) {
      return false;
    }

    const randomId = Math.random().toString(36).substring(2, 7);
    const displayName = name.trim() || 'Site Worker';
    const newUser: AuthUser = {
      id: `USR-${randomId}`,
      name: displayName,
      email: cleanEmail,
      role,
      workerId: workerId?.trim() || `WKR-${randomId.toUpperCase()}`,
      siteLocation: 'Site Execution Sector 4',
      avatarUrl: `https://picsum.photos/seed/${encodeURIComponent(displayName)}/100/100`,
    };

    setUser(newUser);
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(newUser));
    } catch {}
    setIsAuthModalOpen(false);
    return true;
  };

  const switchDemoPersona = (persona: AuthUser) => {
    setUser(persona);
    try {
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(persona));
    } catch {}
  };

  const logout = () => {
    setUser(null);
    try {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } catch {}
  };

  return (
    <AuthContext.Provider
      value={{
        user: mounted ? user : null,
        isAuthModalOpen,
        authModalTab,
        openLoginModal,
        openSignupModal,
        closeAuthModal,
        login,
        signup,
        switchDemoPersona,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
