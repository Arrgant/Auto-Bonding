import { useCallback, useState } from 'react'
import { useAppStore } from '@/store'
import toast from 'react-hot-toast'

export default function FileUploadZone() {
  const { addFile, files, removeFile, clearFiles } = useAppStore()
  const [isDragging, setIsDragging] = useState(false)

  const handleFiles = useCallback((fileList: FileList | null) => {
    if (!fileList) return

    const newFiles = Array.from(fileList)
    const dxfFiles = newFiles.filter((file) => file.name.toLowerCase().endsWith('.dxf'))

    if (dxfFiles.length === 0) {
      toast.error('请上传 DXF 格式文件')
      return
    }

    if (newFiles.length !== dxfFiles.length) {
      toast.warning(`${newFiles.length - dxfFiles.length} 个非 DXF 文件已忽略`)
    }

    dxfFiles.forEach((file) => {
      if (file.size > 10 * 1024 * 1024) {
        toast.error(`文件 ${file.name} 超过 10MB`)
        return
      }
      addFile(file)
    })

    toast.success(`已添加 ${dxfFiles.length} 个文件`)
  }, [addFile])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const handleClick = useCallback(() => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.dxf'
    input.multiple = true
    input.onchange = (e) => {
      const target = e.target as HTMLInputElement
      handleFiles(target.files)
    }
    input.click()
  }, [handleFiles])

  return (
    <div className="bg-dark-card rounded-lg border border-dark-border p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-semibold text-white">文件上传</h3>
        {files.length > 0 && (
          <button
            onClick={clearFiles}
            className="text-sm text-red-400 hover:text-red-300 transition-colors"
          >
            清空
          </button>
        )}
      </div>

      {/* 拖拽区域 */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={handleClick}
        className={`
          border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-all
          ${
            isDragging
              ? 'border-primary-500 bg-primary-900/20'
              : 'border-dark-border hover:border-primary-600 hover:bg-dark-border/50'
          }
        `}
      >
        <div className="text-4xl mb-3">📁</div>
        <p className="text-white font-medium mb-1">点击或拖拽上传 DXF 文件</p>
        <p className="text-sm text-gray-400">支持多文件，单个文件最大 10MB</p>
      </div>

      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2 max-h-64 overflow-auto">
          {files.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-3 p-3 bg-dark-bg rounded-lg border border-dark-border"
            >
              <div className="text-2xl">📄</div>
              <div className="flex-1 min-w-0">
                <p className="text-sm text-white truncate">{file.name}</p>
                <p className="text-xs text-gray-400">
                  {(file.size / 1024).toFixed(1)} KB · {file.status}
                </p>
              </div>
              {file.status === 'pending' && (
                <button
                  onClick={() => removeFile(file.id)}
                  className="text-gray-400 hover:text-red-400 transition-colors"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
              {file.status === 'uploading' && (
                <div className="w-5 h-5 border-2 border-primary-600 border-t-transparent rounded-full animate-spin"></div>
              )}
              {file.status === 'success' && (
                <div className="text-green-500">✓</div>
              )}
              {file.status === 'error' && (
                <div className="text-red-500" title={file.error}>!</div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
