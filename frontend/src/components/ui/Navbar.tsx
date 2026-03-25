import { ReactNode } from 'react';

interface NavbarProps {
  children: ReactNode;
}

export function Navbar({ children }: NavbarProps) {
  return (
    <nav className="h-14 border-b border-border bg-card px-4 flex items-center justify-between">
      {children}
    </nav>
  );
}
