import { useState } from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { StatusBar } from '@/components/layout/StatusBar';
import { ThreeViewer } from '@/components/viewer/ThreeViewer';
import { DXF2DViewer } from '@/components/viewer/DXF2DViewer';
import { ConversionConfigPanel } from '@/components/panels/ConversionConfigPanel';
import { DRCPanel } from '@/components/panels/DRCPanel';
import type { DXFFile, ConvertParams, ConvertTask, DRCResult, BondingCoordinate, ConversionConfig } from '@/types';

const defaultParams: ConvertParams = {
  arcHeight: 200,
  wireDiameter: 25,
  material: 'gold',
  outputFormat: 'csv',
};

const Index = () => {
  const [files, setFiles] = useState<DXFFile[]>([]);
  const [tasks, setTasks] = useState<ConvertTask[]>([]);
  const [params, setParams] = useState<ConvertParams>(defaultParams);
  const [drcResults, setDrcResults] = useState<DRCResult[]>([]);
  const [coordinates, setCoordinates] = useState<BondingCoordinate[]>([]);
  const [logMessages, setLogMessages] = useState<string[]>(['系统就绪']);
  const [activeTab, setActiveTab] = useState<'viewer' | 'params' | 'drc'>('viewer');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dxfBounds, setDxfBounds] = useState<{ minX: number; maxX: number; minY: number; maxY: number } | null>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const addLog = (msg: string) => {
    setLogMessages((prev) => [...prev.slice(-49), `[${new Date().toLocaleTimeString()}] ${msg}`]);
  };

  const handleFilesAdded = (newFiles: File[]) => {
    const dxfFiles: DXFFile[] = newFiles.map((f, i) => ({
      id: `${Date.now()}-${i}`,
      name: f.name,
      size: f.size,
      status: 'pending' as const,
      progress: 0,
      uploadedAt: new Date(),
    }));
    setFiles((prev) => [...prev, ...dxfFiles]);
    
    // 自动选择第一个文件用于显示
    if (newFiles.length > 0 && !selectedFile) {
      setSelectedFile(newFiles[0]);
    }
    
    addLog(`已添加 ${newFiles.length} 个文件`);
  };

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    addLog(`已选择文件：${file.name}`);
  };

  const handleConfigChange = (config: ConversionConfig) => {
    setParams({
      arcHeight: config.loop_height_coefficient * 100,
      wireDiameter: config.default_wire_diameter * 1000,
      material: config.default_material,
      outputFormat: config.export_format,
    });
  };

  const handleConvertFromConfig = (config: ConversionConfig) => {
    handleConfigChange(config);
    handleConvert();
  };

  const handleConvert = () => {
    const pending = files.filter((f) => f.status === 'pending');
    if (pending.length === 0) {
      addLog('没有待转换的文件');
      return;
    }

    const newTasks: ConvertTask[] = pending.map((f) => ({
      id: `task-${f.id}`,
      file: f,
      params,
      status: 'queued' as const,
      progress: 0,
      createdAt: new Date(),
    }));
    setTasks((prev) => [...prev, ...newTasks]);
    addLog(`已创建 ${newTasks.length} 个转换任务`);

    newTasks.forEach((task, idx) => {
      setTimeout(() => {
        setTasks((prev) =>
          prev.map((t) => (t.id === task.id ? { ...t, status: 'processing' as const } : t))
        );
        setFiles((prev) =>
          prev.map((f) => (f.id === task.file.id ? { ...f, status: 'converting' as const } : f))
        );
        addLog(`开始转换：${task.file.name}`);

        let progress = 0;
        const interval = setInterval(() => {
          progress += Math.random() * 20;
          if (progress >= 100) {
            progress = 100;
            clearInterval(interval);
            setTasks((prev) =>
              prev.map((t) => (t.id === task.id ? { ...t, status: 'completed' as const, progress: 100 } : t))
            );
            setFiles((prev) =>
              prev.map((f) => (f.id === task.file.id ? { ...f, status: 'completed' as const, progress: 100 } : f))
            );
            
            // 根据 DXF 边界生成更合理的演示坐标
            const demoCoords: BondingCoordinate[] = Array.from({ length: 12 }, (_, i) => {
              const angle = (i / 12) * Math.PI * 2;
              const radiusX = dxfBounds ? (dxfBounds.maxX - dxfBounds.minX) / 4 : 2;
              const radiusY = dxfBounds ? (dxfBounds.maxY - dxfBounds.minY) / 4 : 2;
              const centerX = dxfBounds ? (dxfBounds.minX + dxfBounds.maxX) / 2 : 0;
              const centerY = dxfBounds ? (dxfBounds.minY + dxfBounds.maxY) / 2 : 0;
              
              return {
                x: centerX + Math.cos(angle) * radiusX,
                y: centerY + Math.sin(angle) * radiusY,
                z: Math.random() * params.arcHeight / 100,
                type: (i % 3 === 0 ? 'ball' : i % 3 === 1 ? 'wedge' : 'stitch') as 'ball' | 'wedge' | 'stitch',
                index: i,
              };
            });
            setCoordinates(demoCoords);
            addLog(`转换完成：${task.file.name}`);
          }
          setTasks((prev) =>
            prev.map((t) => (t.id === task.id ? { ...t, progress: Math.min(progress, 100) } : t))
          );
        }, 300);
      }, idx * 1500);
    });
  };

  const handleDRC = () => {
    if (coordinates.length === 0) {
      addLog('没有可检查的坐标数据');
      return;
    }
    
    addLog('开始 DRC 检查...');
    setTimeout(() => {
      const results: DRCResult[] = [
        { id: '1', severity: 'warning', message: '线弧高度超出推荐范围 (建议 150-250μm)', location: { x: 1.2, y: 0.5 } },
        { id: '2', severity: 'info', message: `检测到 ${coordinates.length} 个焊点，间距符合规范` },
        { id: '3', severity: 'error', message: '焊盘 #7 与相邻焊盘距离过近 (< 50μm)' },
      ];
      setDrcResults(results);
      addLog(`DRC 检查完成：${results.filter((r) => r.severity === 'error').length} 个错误，${results.filter((r) => r.severity === 'warning').length} 个警告`);
    }, 1500);
  };

  const handleRemoveFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
    if (selectedFile && files.find(f => f.id === id)?.name === selectedFile.name) {
      setSelectedFile(null);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const newFiles = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.dxf'));
    if (newFiles.length > 0) {
      handleFilesAdded(newFiles);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background" onDrop={handleDrop} onDragOver={handleDragOver}>
      <Navbar onConvert={handleConvert} onDRC={handleDRC} hasFiles={files.length > 0} />

      <div className="flex flex-1 overflow-hidden">
        <AppSidebar 
          files={files} 
          tasks={tasks} 
          onRemoveFile={handleRemoveFile} 
          onFilesAdded={handleFilesAdded}
          onFileSelect={handleFileSelect}
          selectedFile={selectedFile}
          collapsed={sidebarCollapsed}
          onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        />

        <main className="flex flex-1 flex-col overflow-hidden">
          <div className="flex border-b border-border bg-card">
            {(['viewer', 'params', 'drc'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  activeTab === tab
                    ? 'border-b-2 border-accent text-accent'
                    : 'text-muted-foreground hover:text-foreground'
                }`}
              >
                {tab === 'viewer' ? '视图' : tab === 'params' ? '参数配置' : 'DRC 检查'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'viewer' && (
              <div className="flex h-full">
                {/* 左侧：2D DXF 视图 */}
                <div className="w-1/2 border-r border-border relative">
                  <DXF2DViewer 
                    dxfFile={selectedFile}
                    onDXFLoaded={(entities, bounds) => {
                      setDxfBounds(bounds);
                      addLog(`DXF 加载完成：${entities.length} 个实体`);
                    }}
                  />
                  <div className="absolute top-2 left-2 bg-card/80 backdrop-blur px-3 py-1.5 rounded-md text-xs font-medium border border-border">
                    📐 2D 视图
                  </div>
                </div>

                {/* 右侧：3D 预览 */}
                <div className="w-1/2 relative">
                  {files.length === 0 ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="text-center text-muted-foreground">
                        <div className="text-4xl mb-3">📁</div>
                        <div className="text-lg font-medium">上传 DXF 文件开始</div>
                        <div className="text-sm">支持拖拽或点击上传</div>
                      </div>
                    </div>
                  ) : (
                    <ThreeViewer coordinates={coordinates} />
                  )}
                  <div className="absolute top-2 left-2 bg-card/80 backdrop-blur px-3 py-1.5 rounded-md text-xs font-medium border border-border">
                    🎯 3D 预览
                  </div>
                </div>
              </div>
            )}
            {activeTab === 'params' && (
              <ConversionConfigPanel
                hasFiles={files.length > 0}
                onConvert={handleConvertFromConfig}
                onChange={handleConfigChange}
              />
            )}
            {activeTab === 'drc' && (
              <DRCPanel results={drcResults} onRunDRC={handleDRC} />
            )}
          </div>
        </main>
      </div>

      <StatusBar messages={logMessages} taskCount={tasks.length} completedCount={tasks.filter((t) => t.status === 'completed').length} />
    </div>
  );
};

export default Index;
