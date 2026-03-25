export default function SettingsPage() {
  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-white">设置</h2>
        <p className="text-gray-400 mt-1">配置应用程序</p>
      </div>

      <div className="max-w-2xl space-y-6">
        {/* API 设置 */}
        <div className="bg-dark-card rounded-lg border border-dark-border p-6">
          <h3 className="text-lg font-semibold text-white mb-4">后端 API</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-300 mb-2">API 地址</label>
              <input
                type="text"
                defaultValue="http://localhost:8000"
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
              />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <div className="w-2 h-2 bg-green-500 rounded-full"></div>
              <span className="text-gray-400">后端已连接</span>
            </div>
          </div>
        </div>

        {/* 关于 */}
        <div className="bg-dark-card rounded-lg border border-dark-border p-6">
          <h3 className="text-lg font-semibold text-white mb-4">关于</h3>
          <div className="space-y-2 text-sm text-gray-400">
            <p>
              <span className="text-gray-300">版本：</span>v0.1.0
            </p>
            <p>
              <span className="text-gray-300">GitHub：</span>
              <a
                href="https://github.com/Arrgant/Auto-Bonding"
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-400 hover:underline"
              >
                Arrgant/Auto-Bonding
              </a>
            </p>
            <p>
              <span className="text-gray-300">许可证：</span>MIT
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
