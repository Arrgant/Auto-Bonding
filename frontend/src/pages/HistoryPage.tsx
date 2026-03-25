export default function HistoryPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">历史记录</h2>
        <p className="text-gray-400 mt-1">查看过往转换记录</p>
      </div>

      <div className="flex-1 flex items-center justify-center">
        <div className="text-center text-gray-500">
          <div className="text-6xl mb-4">📜</div>
          <p className="text-lg">暂无历史记录</p>
          <p className="text-sm mt-2">完成转换后，记录将显示在这里</p>
        </div>
      </div>
    </div>
  )
}
