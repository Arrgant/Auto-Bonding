import { useState } from 'react';
import { Navbar } from '@/components/layout/Navbar';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { StatusBar } from '@/components/layout/StatusBar';
import { ThreeViewer } from '@/components/viewer/ThreeViewer';
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
    addLog(`已添加 ${newFiles.length} 个文件`);
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
    if (pending.length === 0) return;

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
            const demoCoords: BondingCoordinate[] = Array.from({ length: 12 }, (_, i) => ({
              x: Math.cos((i / 12) * Math.PI * 2) * 2,
              y: Math.sin((i / 12) * Math.PI * 2) * 2,
              z: Math.random() * params.arcHeight / 100,
              type: (i % 3 === 0 ? 'ball' : i % 3 === 1 ? 'wedge' : 'stitch') as 'ball' | 'wedge' | 'stitch',
              index: i,
            }));
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
    addLog('开始 DRC 检查...');
    setTimeout(() => {
      const results: DRCResult[] = [
        { id: '1', severity: 'warning', message: '线弧高度超出推荐范围 (建议 150-250μm)', location: { x: 1.2, y: 0.5 } },
        { id: '2', severity: 'info', message: '检测到 12 个焊点，间距符合规范' },
        { id: '3', severity: 'error', message: '焊盘 #7 与相邻焊盘距离过近 (< 50μm)' },
      ];
      setDrcResults(results);
      addLog(`DRC 检查完成：${results.filter((r) => r.severity === 'error').length} 个错误，${results.filter((r) => r.severity === 'warning').length} 个警告`);
    }, 1500);
  };

  const handleRemoveFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <Navbar onConvert={handleConvert} onDRC={handleDRC} hasFiles={files.length > 0} />

      <div className="flex flex-1 overflow-hidden">
        <AppSidebar files={files} tasks={tasks} onRemoveFile={handleRemoveFile} onFilesAdded={handleFilesAdded} />

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
                {tab === 'viewer' ? '3D 预览' : tab === 'params' ? '参数配置' : 'DRC 检查'}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-hidden">
            {activeTab === 'viewer' && (
              <div className="relative h-full">
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
