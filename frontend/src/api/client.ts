import axios from 'axios'
import type { 
  Material, 
  FormatInfo, 
  ConversionConfig, 
  DRCReport,
  BatchConversionResult,
  ApiResponse
} from '@/types'

// API 基础 URL - 开发环境使用代理，生产环境可配置
const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || '/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 分钟超时，适合大文件
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const message = error.response?.data?.detail || error.message || '请求失败'
    console.error('API Error:', message)
    return Promise.reject(new Error(message))
  }
)

/**
 * 获取材料列表
 */
export const getMaterials = async (): Promise<Material[]> => {
  const response = await api.get('/materials')
  return (response as any).materials || []
}

/**
 * 获取支持的格式
 */
export const getFormats = async (): Promise<FormatInfo> => {
  const response = await api.get('/formats')
  return response as unknown as FormatInfo
}

/**
 * 转换单个文件
 */
export const convertFile = async (
  file: File,
  config: ConversionConfig,
  onProgress?: (progress: number) => void
): Promise<ApiResponse<any>> => {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('config', JSON.stringify(config))

  const response = await api.post('/convert', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(progress)
      }
    },
  })

  return response as unknown as ApiResponse<any>
}

/**
 * 批量转换
 */
export const convertBatch = async (
  files: File[],
  config: ConversionConfig,
  onProgress?: (filename: string, progress: number) => void
): Promise<BatchConversionResult> => {
  const formData = new FormData()
  files.forEach((file) => {
    formData.append('files', file)
  })
  formData.append('config', JSON.stringify(config))

  const response = await api.post('/convert/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress('uploading', progress)
      }
    },
  })

  return response as unknown as BatchConversionResult
}

/**
 * 运行 DRC 检查
 */
export const runDRC = async (file: File): Promise<DRCReport> => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/drc', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response as unknown as DRCReport
}

/**
 * 获取 IGBT 规则配置
 */
export const getIgbtRules = async (): Promise<{
  modes: Array<{ id: string; name: string; description: string }>
  voltage_classes: Array<{ class: string; name: string; range: string; min_spacing: number }>
  wire_types: Array<{ id: string; name: string; diameters?: number[]; sizes?: string[] }>
  pad_types: Array<{ id: string; name: string; min_size: number; description: string }>
  current_density: Record<string, number>
}> => {
  const response = await api.get('/igbt/rules')
  return response as any
}

/**
 * 计算电流承载能力
 */
export const calculateCurrentCapacity = async (params: {
  wire_type: string
  diameter?: number
  ribbon_width?: number
  ribbon_thickness?: number
}): Promise<{
  wire_type: string
  description: string
  cross_section_mm2: number
  current_density_A_mm2: number
  max_current_A: number
  recommendation: string
}> => {
  const response = await api.get('/igbt/current-capacity', { params })
  return response as any
}

/**
 * 健康检查
 */
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get('/health')
  return response as unknown as { status: string }
}

/**
 * 下载文件
 */
export const downloadFile = async (downloadUrl: string, filename?: string): Promise<void> => {
  // 如果是相对 URL，添加 baseURL
  const url = downloadUrl.startsWith('http') 
    ? downloadUrl 
    : `${API_BASE_URL}${downloadUrl}`
  
  const response = await axios.get(url, {
    responseType: 'blob',
  })
  
  // 创建下载链接
  const blob = new Blob([response.data])
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  
  // 从 URL 提取文件名或使用提供的文件名
  const extractedFilename = filename || downloadUrl.split('/').pop() || 'download'
  link.setAttribute('download', extractedFilename)
  document.body.appendChild(link)
  link.click()
  
  // 清理
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export default api
