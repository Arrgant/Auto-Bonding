import { useState } from 'react';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/Card';
import { ConversionConfig } from '@/types';

interface ConversionConfigPanelProps {
  hasFiles: boolean;
  onConvert: (config: ConversionConfig) => void;
  onChange: (config: ConversionConfig) => void;
}

export function ConversionConfigPanel({ hasFiles, onConvert, onChange }: ConversionConfigPanelProps) {
  const [config, setConfig] = useState<ConversionConfig>({
    loop_height_coefficient: 2.0,
    default_wire_diameter: 0.025,
    default_material: 'gold',
    export_format: 'csv',
  });

  const materials = [
    { id: 'gold', name: '金线 (Au)', coefficient: 1.0 },
    { id: 'copper', name: '铜线 (Cu)', coefficient: 0.8 },
    { id: 'aluminum', name: '铝线 (Al)', coefficient: 0.6 },
  ];

  const formats = [
    { id: 'csv', name: 'CSV' },
    { id: 'json', name: 'JSON' },
    { id: 'txt', name: 'TXT' },
  ];

  const updateConfig = (updates: Partial<ConversionConfig>) => {
    const newConfig = { ...config, ...updates };
    setConfig(newConfig);
    onChange(newConfig);
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <Card>
        <CardHeader>
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span>⚙️</span> 转换参数配置
          </h2>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* 线弧高度系数 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              线弧高度系数：{config.loop_height_coefficient.toFixed(1)}
            </label>
            <input
              type="range"
              min="1.0"
              max="5.0"
              step="0.1"
              value={config.loop_height_coefficient}
              onChange={(e) => updateConfig({ loop_height_coefficient: parseFloat(e.target.value) })}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>1.0</span>
              <span>5.0</span>
            </div>
          </div>

          {/* 线径 */}
          <div>
            <label className="block text-sm font-medium mb-2">
              默认线径：{(config.default_wire_diameter * 1000).toFixed(1)} μm
            </label>
            <input
              type="range"
              min="0.015"
              max="0.050"
              step="0.001"
              value={config.default_wire_diameter}
              onChange={(e) => updateConfig({ default_wire_diameter: parseFloat(e.target.value) })}
              className="w-full accent-primary"
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>15 μm</span>
              <span>50 μm</span>
            </div>
          </div>

          {/* 材料选择 */}
          <div>
            <label className="block text-sm font-medium mb-2">默认材料</label>
            <div className="grid grid-cols-3 gap-2">
              {materials.map((mat) => (
                <button
                  key={mat.id}
                  onClick={() => updateConfig({ default_material: mat.id })}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    config.default_material === mat.id
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:border-accent'
                  }`}
                >
                  {mat.name}
                </button>
              ))}
            </div>
          </div>

          {/* 导出格式 */}
          <div>
            <label className="block text-sm font-medium mb-2">导出格式</label>
            <div className="grid grid-cols-3 gap-2">
              {formats.map((fmt) => (
                <button
                  key={fmt.id}
                  onClick={() => updateConfig({ export_format: fmt.id })}
                  className={`p-3 rounded-lg border text-sm transition-colors ${
                    config.export_format === fmt.id
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border hover:border-accent'
                  }`}
                >
                  {fmt.name}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <button
            onClick={() => onConvert(config)}
            disabled={!hasFiles}
            className="w-full py-3 px-4 bg-primary text-primary-foreground rounded-lg font-medium hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            <span>🚀</span> 开始转换
          </button>
        </CardFooter>
      </Card>
    </div>
  );
}
