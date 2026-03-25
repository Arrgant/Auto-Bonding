import { StatusBar as StatusBarUI } from '@/components/ui/StatusBar';

interface StatusBarProps {
  messages: string[];
  taskCount: number;
  completedCount: number;
}

export function StatusBar({ messages, taskCount, completedCount }: StatusBarProps) {
  const lastMessage = messages[messages.length - 1] || '系统就绪';

  return (
    <StatusBarUI>
      <div className="flex items-center gap-4">
        <span className="flex items-center gap-2">
          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
          {lastMessage}
        </span>
      </div>
      <div className="flex items-center gap-4">
        {taskCount > 0 && (
          <span>任务：{completedCount}/{taskCount}</span>
        )}
        <span>Auto-Bonding v0.2.0</span>
      </div>
    </StatusBarUI>
  );
}
