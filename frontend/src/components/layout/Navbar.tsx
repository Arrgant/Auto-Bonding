import { Navbar as NavbarUI } from '@/components/ui/Navbar';

interface NavbarProps {
  onConvert: () => void;
  onDRC: () => void;
  hasFiles: boolean;
}

export function Navbar({ onConvert, onDRC, hasFiles }: NavbarProps) {
  return (
    <NavbarUI>
      <div className="flex items-center gap-2">
        <span className="text-xl">🔧</span>
        <span className="font-bold text-lg">Auto-Bonding</span>
        <span className="text-xs text-muted-foreground ml-2">键合图转换工具</span>
      </div>
      
      <div className="flex items-center gap-3">
        <button
          onClick={onDRC}
          disabled={!hasFiles}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-border bg-background hover:bg-accent/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          🛡️ DRC 检查
        </button>
        <button
          onClick={onConvert}
          disabled={!hasFiles}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          🚀 开始转换
        </button>
      </div>
    </NavbarUI>
  );
}
