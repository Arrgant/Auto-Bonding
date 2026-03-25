import { ReactNode } from 'react';

interface StatusBarProps {
  children: ReactNode;
}

export function StatusBar({ children }: StatusBarProps) {
  return (
    <footer className="h-8 border-t border-border bg-card px-4 flex items-center justify-between text-xs text-muted-foreground">
      {children}
    </footer>
  );
}
