import { Sidebar } from '@/components/ui/Sidebar';
import { DXFFile, ConvertTask } from '@/types';

interface AppSidebarProps {
  files: DXFFile[];
  tasks: ConvertTask[];
  onRemoveFile: (id: string) => void;
  onFilesAdded: (files: File[]) => void;
}

export function AppSidebar({ files, tasks, onRemoveFile, onFilesAdded }: AppSidebarProps) {
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onFilesAdded(Array.from(e.target.files));
    }
  };

  return (
    <Sidebar>
      {/* 文件上传区 */}
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
          <span>📁</span> 文件列表
        </h3>
        
        <label className="block w-full p-3 border-2 border-dashed border-border rounded-lg text-center cursor-pointer hover:border-accent hover:bg-accent/5 transition-colors">
          <input
            type="file"
            accept=".dxf"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <div className="text-2xl mb-1">📤</div>
          <div className="text-xs text-muted-foreground">点击上传 DXF 文件</div>
        </label>
      </div>

      {/* 文件列表 */}
      <div className="flex-1 overflow-auto p-4">
        {files.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground text-sm">
            <div className="text-3xl mb-2">📭</div>
            <div>暂无文件</div>
          </div>
        ) : (
          <div className="space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className="group flex items-center gap-3 p-3 bg-background rounded-lg border border-border hover:border-accent/50 transition-colors"
              >
                <div className="text-xl">
                  {file.status === 'completed' ? '✅' : file.status === 'converting' ? '⏳' : '📄'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{file.name}</div>
                  <div className="text-xs text-muted-foreground">
                    {(file.size / 1024).toFixed(1)} KB
                  </div>
                  {file.status === 'converting' && (
                    <div className="mt-1 h-1 bg-border rounded-full overflow-hidden">
                      <div
                        className="h-full bg-accent transition-all"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>
                {file.status === 'pending' && (
                  <button
                    onClick={() => onRemoveFile(file.id)}
                    className="opacity-0 group-hover:opacity-100 p-1 hover:bg-destructive/10 rounded transition-all"
                  >
                    <svg className="w-4 h-4 text-muted-foreground hover:text-destructive" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 任务队列 */}
      {tasks.length > 0 && (
        <div className="border-t border-border p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
            <span>📋</span> 任务队列
          </h3>
          <div className="space-y-2 max-h-48 overflow-auto">
            {tasks.slice(-5).map((task) => (
              <div key={task.id} className="flex items-center gap-2 text-xs">
                <span className={task.status === 'completed' ? 'text-green-500' : task.status === 'processing' ? 'text-accent' : 'text-muted-foreground'}>
                  {task.status === 'completed' ? '✓' : task.status === 'processing' ? '⟳' : '○'}
                </span>
                <span className="truncate flex-1">{task.file.name}</span>
                <span className="text-muted-foreground">{Math.round(task.progress)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Sidebar>
  );
}
