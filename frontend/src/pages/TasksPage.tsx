import { useAppStore } from '@/store'
import { format } from 'date-fns'

export default function TasksPage() {
  const { tasks, removeTask, clearCompletedTasks } = useAppStore()

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">转换任务队列</h2>
          <p className="text-gray-400 mt-1">管理和监控所有转换任务</p>
        </div>
        {tasks.some((t) => t.status === 'success' || t.status === 'error') && (
          <button
            onClick={clearCompletedTasks}
            className="px-4 py-2 bg-dark-border text-gray-300 rounded-lg hover:bg-dark-bg transition-colors"
          >
            清空已完成
          </button>
        )}
      </div>

      {tasks.length === 0 ? (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-gray-500">
            <div className="text-6xl mb-4">📋</div>
            <p className="text-lg">暂无任务</p>
            <p className="text-sm mt-2">在首页上传文件并开始转换</p>
          </div>
        </div>
      ) : (
        <div className="flex-1 bg-dark-card rounded-lg border border-dark-border overflow-hidden">
          <table className="w-full">
            <thead className="bg-dark-bg border-b border-dark-border">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">文件名</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">状态</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">进度</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">开始时间</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-gray-300">操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr
                  key={task.id}
                  className="border-b border-dark-border hover:bg-dark-bg/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">📄</span>
                      <span className="text-white">{task.filename}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="flex-1 w-32 bg-dark-bg rounded-full h-2 overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            task.status === 'error'
                              ? 'bg-red-600'
                              : task.status === 'success'
                              ? 'bg-green-600'
                              : 'bg-primary-600'
                          }`}
                          style={{ width: `${task.progress}%` }}
                        ></div>
                      </div>
                      <span className="text-sm text-gray-400 w-12">{task.progress}%</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-400">
                    {format(new Date(task.startTime), 'HH:mm:ss')}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      {task.status === 'success' && (
                        <button className="px-3 py-1 bg-primary-600 text-white text-sm rounded hover:bg-primary-700 transition-colors">
                          下载
                        </button>
                      )}
                      {task.status === 'error' && (
                        <button className="px-3 py-1 bg-dark-border text-gray-300 text-sm rounded hover:bg-dark-bg transition-colors">
                          重试
                        </button>
                      )}
                      <button
                        onClick={() => removeTask(task.id)}
                        className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                      >
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const badges = {
    pending: { bg: 'bg-gray-600', text: '等待中' },
    processing: { bg: 'bg-blue-600', text: '转换中' },
    success: { bg: 'bg-green-600', text: '成功' },
    error: { bg: 'bg-red-600', text: '失败' },
  }

  const badge = badges[status as keyof typeof badges] || badges.pending

  return (
    <span className={`px-2 py-1 ${badge.bg} text-white text-xs rounded`}>
      {badge.text}
    </span>
  )
}
