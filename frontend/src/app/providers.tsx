'use client';

import { SessionProvider } from 'next-auth/react';
import { ReactNode } from 'react';
import { useUISettings } from '@/lib/store';
import { useEffect } from 'react';

export function Providers({ children }: { children: ReactNode }) {
  const { theme } = useUISettings();

  useEffect(() => {
    const root = document.documentElement;
    root.classList.remove('light', 'dark');
    if (theme === 'system') {
      const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
      root.classList.add(systemTheme);
    } else {
      root.classList.add(theme);
    }
  }, [theme]);

  return (
    <SessionProvider>
      {children}
    </SessionProvider>
  );
}