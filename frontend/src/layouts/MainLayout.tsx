import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAppStore } from '@/store'

export default function MainLayout() {
  const { sidebarOpen, toggleSidebar } = useAppStore()
  const location = useLocation()

  const navItems = [
    { path: '/', label: '首页', icon: '🏠' },
    { path: '/tasks', label: '任务队列', icon: '📋' },
    { path: '/history', label: '历史记录', icon: '📜' },
    { path: '/settings', label: '设置', icon: '⚙️' },
  ]

  return (
    <div className="flex h-screen bg-dark-bg">
      {/* 左侧边栏 */}
      <aside
        className={`${
          sidebarOpen ? 'w-64' : 'w-0'
        } bg-dark-card border-r border-dark-border transition-all duration-300 overflow-hidden flex flex-col`}
      >
        {/* Logo */}
        <div className="p-4 border-b border-dark-border">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <span className="text-2xl">🔧</span>
            Auto-Bonding
          </h1>
          <p className="text-xs text-gray-400 mt-1">键合图转换工具</p>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map((item) => (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                    location.pathname === item.path
                      ? 'bg-primary-800 text-white'
                      : 'text-gray-300 hover:bg-dark-border'
                  }`}
                >
                  <span>{item.icon}</span>
                  <span>{item.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </nav>

        {/* 底部状态 */}
        <div className="p-4 border-t border-dark-border">
          <div className="flex items-center gap-2 text-sm">
            <div className="w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-gray-400">后端在线</span>
          </div>
          <p className="text-xs text-gray-500 mt-2">v0.1.0</p>
        </div>
      </aside>

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部导航栏 */}
        <header className="h-14 bg-dark-card border-b border-dark-border flex items-center px-4 gap-4">
          <button
            onClick={toggleSidebar}
            className="p-2 hover:bg-dark-border rounded-lg transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex-1"></div>

          <div className="flex items-center gap-4">
            <a
              href="https://github.com/Arrgant/Auto-Bonding"
              target="_blank"
              rel="noopener noreferrer"
              className="text-gray-400 hover:text-white transition-colors"
              title="GitHub"
            >
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
            </a>
            <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center text-sm font-bold">
              A
            </div>
          </div>
        </header>

        {/* 内容区 */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>

        {/* 底部状态栏 */}
        <footer className="h-8 bg-dark-card border-t border-dark-border flex items-center px-4 text-xs text-gray-500">
          <span>Auto-Bonding v0.1.0</span>
          <span className="mx-2">|</span>
          <span>后端：http://localhost:8000</span>
        </footer>
      </div>
    </div>
  )
}
