import { createContext, useContext, useEffect, useMemo, useState } from 'react';

export type Theme = 'dark' | 'light' | 'system';
type ResolvedTheme = Exclude<Theme, 'system'>;

const DEFAULT_THEME: Theme = 'dark';
const THEME_STORAGE_KEY = 'vite-ui-theme';

type ThemeProviderProps = {
  children: React.ReactNode;
  defaultTheme?: Theme;
  storageKey?: string;
};

type ThemeProviderState = {
  defaultTheme: Theme;
  resolvedTheme: ResolvedTheme;
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resetTheme: () => void;
};

const ThemeContext = createContext<ThemeProviderState | null>(null);

function readStoredTheme(storageKey: string, fallback: Theme): Theme {
  if (typeof window === 'undefined') return fallback;
  const stored = window.localStorage.getItem(storageKey);
  if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  return fallback;
}

export function ThemeProvider({
  children,
  defaultTheme = DEFAULT_THEME,
  storageKey = THEME_STORAGE_KEY,
}: ThemeProviderProps) {
  const [theme, setThemeState] = useState<Theme>(() => readStoredTheme(storageKey, defaultTheme));

  const resolvedTheme = useMemo((): ResolvedTheme => {
    if (theme !== 'system') return theme;
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }, [theme]);

  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const apply = (next: ResolvedTheme) => {
      root.classList.remove('light', 'dark');
      root.classList.add(next);
      root.setAttribute('data-theme', next);
    };
    const onChange = () => {
      if (theme === 'system') apply(media.matches ? 'dark' : 'light');
    };
    apply(resolvedTheme);
    media.addEventListener('change', onChange);
    return () => media.removeEventListener('change', onChange);
  }, [theme, resolvedTheme]);

  const setTheme = (next: Theme) => {
    window.localStorage.setItem(storageKey, next);
    setThemeState(next);
  };

  const resetTheme = () => {
    window.localStorage.removeItem(storageKey);
    setThemeState(defaultTheme);
  };

  const value = { defaultTheme, resolvedTheme, theme, setTheme, resetTheme };

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) throw new Error('useTheme must be used within a ThemeProvider');
  return context;
}
