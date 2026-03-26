import { useEffect, useState } from 'react'
import { useForm, Controller } from 'react-hook-form'
import { useAppStore } from '@/store'
import { useQuery } from '@tanstack/react-query'
import { getMaterials, getFormats, getIgbtRules } from '@/api/client'
import toast from 'react-hot-toast'

export default function ConversionConfig() {
  const { config, setConfig, files } = useAppStore()
  const [mode, setMode] = useState<'standard' | 'igbt' | 'automotive'>('standard')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const { register, handleSubmit, control, watch, setValue } = useForm({
    defaultValues: {
      ...config,
      mode: 'standard',
      operating_voltage: 600,
      wire_type: 'al_wire',
    },
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

  // 获取 IGBT 规则
  const { data: igbtRules } = useQuery({
    queryKey: ['igbtRules'],
    queryFn: getIgbtRules,
    enabled: mode !== 'standard',
  })

  // 同步到 store
  useEffect(() => {
    setConfig({ ...formData, mode })
  }, [formData, mode, setConfig])

  // 模式切换时更新默认值
  useEffect(() => {
    if (mode === 'igbt' || mode === 'automotive') {
      setValue('default_wire_diameter', 0.3)
      setValue('default_material', 'aluminum')
      setValue('loop_height_coefficient', 2.0)
      setValue('wire_type', 'al_wire')
    } else {
      setValue('default_wire_diameter', 0.025)
      setValue('default_material', 'gold')
      setValue('loop_height_coefficient', 1.5)
    }
  }, [mode, setValue])

  const onSubmit = async () => {
    if (files.length === 0) {
      toast('请先选择文件')
      return
    }

    toast.success(`开始转换 (模式：${mode})...`)
  }

  return (
    <div className="bg-dark-card rounded-lg border border-dark-border p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">转换参数</h3>
        
        {/* 模式选择 */}
        <div className="flex gap-2">
          <button
            onClick={() => setMode('standard')}
            className={`px-3 py-1 rounded text-sm transition-all ${
              mode === 'standard'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-bg text-gray-400 hover:text-white'
            }`}
          >
            标准 IC
          </button>
          <button
            onClick={() => setMode('igbt')}
            className={`px-3 py-1 rounded text-sm transition-all ${
              mode === 'igbt'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-bg text-gray-400 hover:text-white'
            }`}
          >
            IGBT
          </button>
          <button
            onClick={() => setMode('automotive')}
            className={`px-3 py-1 rounded text-sm transition-all ${
              mode === 'automotive'
                ? 'bg-primary-600 text-white'
                : 'bg-dark-bg text-gray-400 hover:text-white'
            }`}
          >
            车规级
          </button>
        </div>
      </div>

      {/* IGBT 模式提示 */}
      {mode !== 'standard' && (
        <div className="mb-4 p-3 bg-blue-900/30 border border-blue-700 rounded-lg">
          <p className="text-sm text-blue-200">
            🔌 <strong>IGBT 功率器件模式</strong>
            {mode === 'automotive' && ' (AEC-Q100 车规标准)'}
          </p>
          <p className="text-xs text-blue-300 mt-1">
            • 默认铝线 300μm • 弧高系数 2.0 • 间距要求更严格
          </p>
        </div>
      )}

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {/* 工作电压 (IGBT 模式) */}
        {(mode === 'igbt' || mode === 'automotive') && (
          <div>
            <label className="block text-sm text-gray-300 mb-2">
              工作电压 (V)
              <span className="text-gray-500 ml-2">
                ({formData.operating_voltage <= 100 ? '低压' :
                  formData.operating_voltage <= 600 ? '中压' :
                  formData.operating_voltage <= 1200 ? '高压' : '超高压'}
                )
              </span>
            </label>
            <input
              type="number"
              step="50"
              {...register('operating_voltage', { valueAsNumber: true })}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
            />
            <p className="text-xs text-gray-500 mt-1">
              电压等级将自动确定最小电气间距要求
            </p>
          </div>
        )}

        {/* 引线类型 (IGBT 模式) */}
        {(mode === 'igbt' || mode === 'automotive') && (
          <div>
            <label className="block text-sm text-gray-300 mb-2">引线类型</label>
            <Controller
              name="wire_type"
              control={control}
              render={({ field }) => (
                <select
                  {...field}
                  value={field.value}
                  className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
                >
                  <option value="al_wire">铝线 (100-500μm)</option>
                  <option value="al_ribbon">铝带 (大电流)</option>
                  <option value="cu_wire">铜线</option>
                </select>
              )}
            />
          </div>
        )}

        {/* 弧高系数 */}
        <div>
          <label className="block text-sm text-gray-300 mb-2">
            弧高系数
            <span className="text-gray-500 ml-2">(默认 {mode === 'standard' ? '1.5' : '2.0'})</span>
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
          <label className="block text-sm text-gray-300 mb-2">
            线径 (mm)
            {mode !== 'standard' && (
              <span className="text-gray-500 ml-2">IGBT 推荐 ≥0.3mm</span>
            )}
          </label>
          <Controller
            name="default_wire_diameter"
            control={control}
            render={({ field }) => (
              <select
                {...field}
                value={field.value}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-white focus:outline-none focus:border-primary-600"
              >
                {mode === 'standard' ? (
                  <>
                    <option value={0.015}>0.015 mm</option>
                    <option value={0.02}>0.020 mm</option>
                    <option value={0.025}>0.025 mm</option>
                    <option value={0.03}>0.030 mm</option>
                    <option value={0.04}>0.040 mm</option>
                  </>
                ) : (
                  <>
                    <option value={0.1}>0.100 mm (100μm)</option>
                    <option value={0.15}>0.150 mm (150μm)</option>
                    <option value={0.2}>0.200 mm (200μm)</option>
                    <option value={0.25}>0.250 mm (250μm)</option>
                    <option value={0.3}>0.300 mm (300μm)</option>
                    <option value={0.375}>0.375 mm (375μm)</option>
                    <option value={0.4}>0.400 mm (400μm)</option>
                    <option value={0.5}>0.500 mm (500μm)</option>
                  </>
                )}
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
                    {m.name} {m.typical_use && `(${m.typical_use})`}
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

        {/* 高级选项 */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            {showAdvanced ? '▼ 隐藏高级选项' : '▶ 显示高级选项'}
          </button>
          
          {showAdvanced && (
            <div className="mt-3 p-3 bg-dark-bg rounded-lg border border-dark-border space-y-3">
              <p className="text-xs text-gray-500">
                高级选项通常不需要修改，除非有特殊工艺要求。
              </p>
              {/* 可以添加更多高级参数 */}
            </div>
          )}
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
                : mode === 'standard'
                ? 'bg-primary-600 text-white hover:bg-primary-700'
                : 'bg-green-600 text-white hover:bg-green-700'
            }
          `}
        >
          {files.length === 0 ? '请先选择文件' : 
           mode === 'standard' ? '开始转换' : 
           '开始转换 (IGBT DRC 检查)'}
        </button>
      </form>
    </div>
  )
}