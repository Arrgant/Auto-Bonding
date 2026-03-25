import { Card, CardHeader, CardContent } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { DRCResult } from '@/types';

interface DRCPanelProps {
  results: DRCResult[];
  onRunDRC: () => void;
}

export function DRCPanel({ results, onRunDRC }: DRCPanelProps) {
  const errorCount = results.filter((r) => r.severity === 'error').length;
  const warningCount = results.filter((r) => r.severity === 'warning').length;
  const infoCount = results.filter((r) => r.severity === 'info').length;

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <span>🛡️</span> DRC 设计规则检查
          </h2>
          <button
            onClick={onRunDRC}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            运行检查
          </button>
        </CardHeader>
        <CardContent>
          {results.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <div className="text-4xl mb-3">🔍</div>
              <div className="text-lg font-medium">暂无检查结果</div>
              <div className="text-sm">点击"运行检查"开始 DRC 验证</div>
            </div>
          ) : (
            <div className="space-y-4">
              {/* 统计摘要 */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-center">
                  <div className="text-2xl font-bold text-red-500">{errorCount}</div>
                  <div className="text-xs text-red-400">错误</div>
                </div>
                <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20 text-center">
                  <div className="text-2xl font-bold text-yellow-500">{warningCount}</div>
                  <div className="text-xs text-yellow-400">警告</div>
                </div>
                <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/20 text-center">
                  <div className="text-2xl font-bold text-blue-500">{infoCount}</div>
                  <div className="text-xs text-blue-400">提示</div>
                </div>
              </div>

              {/* 问题列表 */}
              <div className="space-y-2">
                {results.map((result) => (
                  <div
                    key={result.id}
                    className="p-4 rounded-lg border bg-background flex items-start gap-3"
                  >
                    <div className="text-xl mt-0.5">
                      {result.severity === 'error' ? '❌' : result.severity === 'warning' ? '⚠️' : 'ℹ️'}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant={result.severity === 'error' ? 'error' : result.severity === 'warning' ? 'warning' : 'info'}>
                          {result.severity.toUpperCase()}
                        </Badge>
                        {result.location && (
                          <span className="text-xs text-muted-foreground">
                            位置：({result.location.x.toFixed(2)}, {result.location.y.toFixed(2)})
                          </span>
                        )}
                      </div>
                      <p className="text-sm">{result.message}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
