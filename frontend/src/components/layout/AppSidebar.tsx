import { Sidebar } from '@/components/ui/Sidebar';
import { DXFFile, ConvertTask } from '@/types';

interface AppSidebarProps {
  files: DXFFile[];
  tasks: ConvertTask[];
  onRemoveFile: (id: string) => void;
  onFilesAdded: (files: File[]) => void;
  onFileSelect?: (file: File) => void;
  selectedFile?: File | null;
  collapsed?: boolean;
  onToggle?: () => void;
}

export function AppSidebar({ 
  files, 
  tasks, 
  onRemoveFile, 
  onFilesAdded, 
  onFileSelect, 
  selectedFile,
  collapsed = false,
  onToggle
}: AppSidebarProps) {
  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      onFilesAdded(Array.from(e.target.files));
    }
  };

  const handleFileClick = (file: DXFFile) => {
    if (onFileSelect) {
      const fileObj = new File([], file.name);
      onFileSelect(fileObj);
    }
  };

  return (
    <Sidebar collapsed={collapsed} onToggle={onToggle}>
      {/* 展开状态 - 显示完整文件列表 */}
      {!collapsed && (
        <>
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
                    onClick={() => handleFileClick(file)}
                    className={`group flex items-center gap-3 p-3 rounded-lg border transition-all cursor-pointer ${
                      selectedFile?.name === file.name
                        ? 'bg-accent/10 border-accent'
                        : 'bg-background hover:border-accent/50'
                    }`}
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
                        onClick={(e) => {
                          e.stopPropagation();
                          onRemoveFile(file.id);
                        }}
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
        </>
      )}
      
      {/* 收起状态 - 显示简化文件列表 */}
      {collapsed && (
        <div className="w-12 flex flex-col items-center py-4 gap-3 overflow-hidden">
          {/* 上传按钮 */}
          <label 
            className="cursor-pointer p-2 rounded-lg hover:bg-accent/10 transition-colors"
            title="上传 DXF 文件"
          >
            <input
              type="file"
              accept=".dxf"
              multiple
              onChange={handleFileSelect}
              className="hidden"
            />
            <div className="text-xl">📤</div>
          </label>
          
          {/* 文件计数 */}
          {files.length > 0 && (
            <div className="text-xs font-medium text-muted-foreground">
              {files.length}
            </div>
          )}
          
          {/* 文件列表缩略 */}
          {files.length > 0 && (
            <div className="flex-1 overflow-hidden flex flex-col gap-1 w-full px-1">
              {files.slice(0, 5).map((file) => (
                <div
                  key={file.id}
                  onClick={() => handleFileClick(file)}
                  className={`text-lg cursor-pointer hover:scale-110 transition-transform ${
                    selectedFile?.name === file.name ? 'opacity-100' : 'opacity-50'
                  }`}
                  title={file.name}
                >
                  {file.status === 'completed' ? '✅' : file.status === 'converting' ? '⏳' : '📄'}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </Sidebar>
  );
}
