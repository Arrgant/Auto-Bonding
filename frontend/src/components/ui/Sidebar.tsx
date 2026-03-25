import { ReactNode } from 'react';

interface SidebarProps {
  children: ReactNode;
  className?: string;
}

export function Sidebar({ children, className = '' }: SidebarProps) {
  return (
    <aside className={`w-72 border-r border-border bg-card flex flex-col ${className}`}>
      {children}
    </aside>
  );
}
