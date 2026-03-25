import FileUploadZone from '@/components/FileUploadZone'
import ConversionConfig from '@/components/ConversionConfig'
import ModelViewer3D from '@/components/ModelViewer3D'
import { useAppStore } from '@/store'

export default function HomePage() {
  const { files, tasks } = useAppStore()

  return (
    <div className="h-full flex flex-col">
      {/* 标题 */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">键合图转换</h2>
        <p className="text-gray-400 mt-1">上传 DXF 文件，自动转换为 3D 模型并导出打线坐标</p>
      </div>

      {/* 主内容区 */}
      <div className="flex-1 grid grid-cols-12 gap-6 min-h-0">
        {/* 左侧：上传和配置 */}
        <div className="col-span-4 flex flex-col gap-6 overflow-auto">
          {/* 文件上传 */}
          <FileUploadZone />

          {/* 参数配置 */}
          <ConversionConfig />

          {/* 文件列表 */}
          {files.length > 0 && (
            <div className="bg-dark-card rounded-lg border border-dark-border p-4">
              <h3 className="text-lg font-semibold text-white mb-3">
                已选择 {files.length} 个文件
              </h3>
              <ul className="space-y-2 max-h-48 overflow-auto">
                {files.map((file) => (
                  <li
                    key={file.id}
                    className="flex items-center justify-between text-sm p-2 bg-dark-bg rounded"
                  >
                    <span className="text-gray-300 truncate flex-1">{file.name}</span>
                    <span className="text-gray-500 ml-2">
                      {(file.size / 1024).toFixed(1)} KB
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* 右侧：3D 预览 */}
        <div className="col-span-8 bg-dark-card rounded-lg border border-dark-border overflow-hidden">
          <ModelViewer3D />
        </div>
      </div>

      {/* 任务进度 */}
      {tasks.some((t) => t.status === 'processing') && (
        <div className="mt-4 bg-dark-card rounded-lg border border-dark-border p-4">
          <h3 className="text-lg font-semibold text-white mb-3">转换进度</h3>
          <div className="space-y-2">
            {tasks
              .filter((t) => t.status === 'processing')
              .map((task) => (
                <div key={task.id} className="flex items-center gap-3">
                  <span className="text-sm text-gray-300 w-32 truncate">{task.filename}</span>
                  <div className="flex-1 bg-dark-bg rounded-full h-2 overflow-hidden">
                    <div
                      className="bg-primary-600 h-full transition-all duration-300"
                      style={{ width: `${task.progress}%` }}
                    ></div>
                  </div>
                  <span className="text-sm text-gray-400 w-12 text-right">{task.progress}%</span>
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}
