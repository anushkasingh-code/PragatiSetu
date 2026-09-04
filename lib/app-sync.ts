'use client';

import { useEffect } from 'react';

export const APP_DATA_REFRESH_EVENT = 'pragati:data-refresh';

export type AppDataRefreshDetail = {
  source?: string;
};

export function notifyAppDataRefresh(detail?: AppDataRefreshDetail) {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent<AppDataRefreshDetail>(APP_DATA_REFRESH_EVENT, { detail }));
}

export function useAppDataRefresh(callback: () => void) {
  useEffect(() => {
    const handler = () => callback();
    window.addEventListener(APP_DATA_REFRESH_EVENT, handler);
    return () => window.removeEventListener(APP_DATA_REFRESH_EVENT, handler);
  }, [callback]);
}
