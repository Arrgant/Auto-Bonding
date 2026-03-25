import { useEffect } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { useAppStore } from '@/store'
import { useQuery } from '@tanstack/react-query'
import { getMaterials, getFormats } from '@/api/client'
import toast from 'react-hot-toast'

export default function ConversionConfig() {
  const { config, setConfig, files } = useAppStore()

  const { register, handleSubmit, control, watch } = useForm({
    defaultValues: config,
  })

  const formData = watch()

  // 获取材料列表
  const { data: materials } = useQuery({
    queryKey: ['materials'],
    queryFn: getMaterials,
  })

  // 获取格式列表
  const { data: formats } = useQuery({
    queryKey: ['formats'],
    queryFn: getFormats,
  })

  // 同步到 store
  useEffect(() => {
    setConfig(formData)
  }, [formData, setConfig])

  const onSubmit = async () => {
    if (files.length === 0) {
      toast.warning('请先选择文件')
      return
    }

    toast.success('开始转换...')
    // 转换逻辑将在 HomePage 或单独的服务中实现
  }

  return (
    <div className="bg-dark-card rounded-lg border border-dark-border p-4">
      <h3 className="text-lg font-semibold text-white mb-4">转换参数</h3>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* 弧高系数 */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">
            弧高系数
            <span className="text-gray-500 ml-2">(默认 1.5)</span>
          </label>
          <div className="flex items-center gap-3">
            <input
              type="range"
              min="0.1"
              max="10.0"
              step="0.1"
              {...register('loop_height_coefficient', { valueAsNumber: true })}
              className="flex-1 h-2 bg-dark-border rounded-lg appearance-none cursor-pointer"
            />
            <span className="text-white font-mono w-16 text-right">
              {formData.loop_height_coefficient.toFixed(1)}
            </span>
          </div>
        </div>

        {/* 线径 */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">线径 (mm)</label>
          <Controller
            name="default_wire_diameter"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                value={field.value}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
              >
                <option value={0.015}>0.015 mm</option>
                <option value={0.02}>0.020 mm</option>
                <option value={0.025}>0.025 mm</option>
                <option value={0.03}>0.030 mm</option>
                <option value={0.04}>0.040 mm</option>
              </select>
            )}
          />
        </div>

        {/* 材料 */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">材料</label>
          <Controller
            name="default_material"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                value={field.value}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
              >
                {materials?.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name} (系数：{m.coefficient})
                  </option>
                ))}
              </select>
            )}
          />
        </div>

        {/* 导出格式 */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">导出格式</label>
          <Controller
            name="export_format"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                value={field.value}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
              >
                <optgroup label="3D 格式">
                  {formats?.['3d']?.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="坐标格式">
                  {formats?.coordinates?.map((f) => (
                    <option key={f} value={f}>
                      {f}
                    </option>
                  ))}
                </optgroup>
              </select>
            )}
          />
        </div>

        {/* 开始转换按钮 */}
        <button
          type="submit"
          disabled={files.length === 0}
          className={`
            w-full py-3 rounded-lg font-semibold transition-all
            ${
              files.length === 0
                ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                : 'bg-primary-600 text-white hover:bg-primary-700'
            }
          `}
        >
          {files.length === 0 ? '请先选择文件' : '开始转换'}
        </button>
      </form>
    </div>
  )
}
