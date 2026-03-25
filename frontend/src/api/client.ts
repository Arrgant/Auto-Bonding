import axios from 'axios'
import type { 
  Material, 
  FormatInfo, 
  ConversionConfig, 
  DRCReport,
  BatchConversionResult 
} from '@/types'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
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
  return response.materials || []
}

/**
 * 获取支持的格式
 */
export const getFormats = async (): Promise<FormatInfo> => {
  const response = await api.get('/formats')
  return response
}

/**
 * 转换单个文件
 */
export const convertFile = async (
  file: File,
  config: ConversionConfig,
  onProgress?: (progress: number) => void
) => {
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

  return response
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
  })

  return response
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

  return response
}

/**
 * 健康检查
 */
export const healthCheck = async (): Promise<{ status: string }> => {
  const response = await api.get('/health')
  return response
}

/**
 * 下载文件
 */
export const downloadFile = async (url: string): Promise<Blob> => {
  const response = await api.get(url, {
    responseType: 'blob',
  })
  return response
}

export default api
