import { ReactNode } from 'react';

interface SidebarProps {
  children: ReactNode;
  className?: string;
  collapsed?: boolean;
  onToggle?: () => void;
}

export function Sidebar({ children, className = '', collapsed = false, onToggle }: SidebarProps) {
  return (
    <div className="flex">
      {/* 收起/展开按钮 - 放在侧边栏左侧 */}
      {onToggle && (
        <button
          onClick={onToggle}
          className="w-6 flex-shrink-0 flex items-center justify-center bg-card border-r border-border hover:bg-accent/10 transition-colors"
          title={collapsed ? '展开侧边栏' : '收起侧边栏'}
        >
          <svg 
            className={`w-4 h-4 text-muted-foreground transition-transform duration-300 ${collapsed ? 'rotate-180' : ''}`}
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      )}
      
      {/* 侧边栏主体 */}
      <div 
        className={`flex-shrink-0 transition-all duration-300 ease-in-out overflow-hidden ${
          collapsed ? 'w-0' : 'w-72'
        }`}
      >
        <aside className={`border-r border-border bg-card flex flex-col h-full ${className}`}>
          {children}
        </aside>
      </div>
    </div>
  );
}
