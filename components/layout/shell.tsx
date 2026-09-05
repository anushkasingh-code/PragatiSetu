'use client';

import { useState, useEffect } from 'react';
import { Sidebar } from './sidebar';
import { Header } from './header';
import { AuthProvider } from '@/lib/auth-context';
import { AuthModal } from '@/components/auth/auth-modal';
import { AiChatDrawer } from '@/components/ai/ai-chat-drawer';

export function Shell({ children }: { children: React.ReactNode }) {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  useEffect(() => {
    try {
      const stored = localStorage.getItem('pragatisetu:worker-preferences');
      if (stored) {
        const prefs = JSON.parse(stored);
        const root = document.documentElement;

        // Apply Theme
        if (prefs.theme === 'dark') {
          root.classList.add('dark');
        } else if (prefs.theme === 'light') {
          root.classList.remove('dark');
        } else if (prefs.theme === 'system') {
          if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
            root.classList.add('dark');
          } else {
            root.classList.remove('dark');
          }
        }

        // Apply High Contrast
        if (prefs.highContrast) {
          root.classList.add('high-contrast');
        } else {
          root.classList.remove('high-contrast');
        }
      }
    } catch {}
  }, []);

  return (
    <AuthProvider>
      <div className="flex h-screen overflow-hidden antialiased selection:bg-primary/20 selection:text-primary">
        <Sidebar isOpen={isMobileMenuOpen} onClose={() => setIsMobileMenuOpen(false)} />
        <div className="flex-1 flex flex-col min-w-0 bg-surface relative">
          <Header onMenuClick={() => setIsMobileMenuOpen(true)} />
          <main className="flex-1 overflow-y-auto">
            {children}
          </main>
        </div>
      </div>
      <AuthModal />
      <AiChatDrawer />
    </AuthProvider>
  );
}
