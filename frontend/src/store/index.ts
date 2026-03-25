import { create } from 'zustand'
import type { UploadFile, ConversionTask, ConversionConfig } from '@/types'

interface AppState {
  // 上传文件
  files: UploadFile[]
  addFile: (file: File) => void
  removeFile: (id: string) => void
  clearFiles: () => void
  updateFileStatus: (id: string, status: UploadFile['status'], progress?: number, error?: string) => void

  // 转换配置
  config: ConversionConfig
  setConfig: (config: Partial<ConversionConfig>) => void
  resetConfig: () => void

  // 转换任务
  tasks: ConversionTask[]
  addTask: (task: ConversionTask) => void
  updateTask: (id: string, updates: Partial<ConversionTask>) => void
  removeTask: (id: string) => void
  clearCompletedTasks: () => void

  // UI 状态
  sidebarOpen: boolean
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

const defaultConfig: ConversionConfig = {
  loop_height_coefficient: 1.5,
  default_wire_diameter: 0.025,
  default_material: 'gold',
  export_format: 'STEP',
}

export const useAppStore = create<AppState>((set) => ({
  // 文件管理
  files: [],
  addFile: (file: File) =>
    set((state) => ({
      files: [
        ...state.files,
        {
          id: Math.random().toString(36).substr(2, 9),
          file,
          name: file.name,
          size: file.size,
          status: 'pending',
          progress: 0,
        },
      ],
    })),
  removeFile: (id: string) =>
    set((state) => ({
      files: state.files.filter((f) => f.id !== id),
    })),
  clearFiles: () => set({ files: [] }),
  updateFileStatus: (id: string, status: UploadFile['status'], progress?: number, error?: string) =>
    set((state) => ({
      files: state.files.map((f) =>
        f.id === id ? { ...f, status, progress: progress ?? f.progress, error } : f
      ),
    })),

  // 配置管理
  config: defaultConfig,
  setConfig: (config: Partial<ConversionConfig>) =>
    set((state) => ({
      config: { ...state.config, ...config },
    })),
  resetConfig: () => set({ config: defaultConfig }),

  // 任务管理
  tasks: [],
  addTask: (task: ConversionTask) =>
    set((state) => ({
      tasks: [...state.tasks, task],
    })),
  updateTask: (id: string, updates: Partial<ConversionTask>) =>
    set((state) => ({
      tasks: state.tasks.map((t) => (t.id === id ? { ...t, ...updates } : t)),
    })),
  removeTask: (id: string) =>
    set((state) => ({
      tasks: state.tasks.filter((t) => t.id !== id),
    })),
  clearCompletedTasks: () =>
    set((state) => ({
      tasks: state.tasks.filter((t) => t.status !== 'success' && t.status !== 'error'),
    })),

  // UI 状态
  sidebarOpen: true,
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setSidebarOpen: (open: boolean) => set({ sidebarOpen: open }),
}))
