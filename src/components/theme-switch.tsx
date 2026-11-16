import { useEffect } from 'react';
import { Check, Moon, Sun } from '@/components/common/icons';
import { cn } from '@/lib/utils';
import { useTheme } from '@/context/theme-provider';
import { Button } from '@/components/ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';

export function ThemeSwitch() {
  const { theme, setTheme } = useTheme();

  useEffect(() => {
    const themeColor = theme === 'dark' ? '#0f1716' : '#eef1ef';
    const meta = document.querySelector("meta[name='theme-color']");
    if (meta) meta.setAttribute('content', themeColor);
  }, [theme]);

  return (
    <DropdownMenu modal={false}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 scale-95 rounded-none" aria-label="Toggle theme">
          <Sun className="h-[1.1rem] w-[1.1rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute h-[1.1rem] w-[1.1rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setTheme('light')}>
          Light
          <Check className={cn('ml-auto h-3.5 w-3.5', theme !== 'light' && 'hidden')} />
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('dark')}>
          Dark
          <Check className={cn('ml-auto h-3.5 w-3.5', theme !== 'dark' && 'hidden')} />
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setTheme('system')}>
          System
          <Check className={cn('ml-auto h-3.5 w-3.5', theme !== 'system' && 'hidden')} />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
