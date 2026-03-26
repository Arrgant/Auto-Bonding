// 材料类型
export interface Material {
  id: string;
  name: string;
  coefficient: number;
  typical_use?: string;  // 典型用途
}

// 导出格式
export interface FormatInfo {
  '3d': string[];
  coordinates: string[];
}

// 转换配置
export interface ConversionConfig {
  loop_height_coefficient: number;
  default_wire_diameter: number;
  default_material: string;
  export_format: string;
  // IGBT 特定字段
  mode?: 'standard' | 'igbt' | 'automotive';
  operating_voltage?: number;
  wire_type?: 'al_wire' | 'al_ribbon' | 'cu_wire';
  expected_current?: number;
}

// 上传文件
export interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
}

// 转换任务
export interface ConversionTask {
  id: string;
  filename: string;
  fileSize: number;
  status: 'pending' | 'processing' | 'success' | 'error';
  progress: number;
  startTime: Date;
  endTime?: Date;
  result?: {
    downloadUrl: string;
    previewUrl: string;
  };
  error?: string;
}

// DRC 违规
export interface DRCViolation {
  type: 'spacing' | 'height' | 'width' | 'span' | 'current' | 'voltage_spacing' | 'pad_size';
  severity: 'error' | 'warning';
  description: string;
  actual_value: number;
  required_value: number;
  location?: {
    x: number;
    y: number;
    z: number;
  };
  category?: 'general' | 'igbt' | 'electrical' | 'mechanical';  // 规则类别
}

// DRC 报告
export interface DRCReport {
  passed: boolean;
  total_violations: number;
  errors: number;
  warnings: number;
  violations: DRCViolation[];
  check_duration?: number;
}

// API 响应
export interface ApiResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

// 批量转换响应
export interface BatchConversionResult {
  total: number;
  success: number;
  results: Array<{
    filename: string;
    success: boolean;
    message: string;
  }>;
}

// DXF 文件（新界面用）
export interface DXFFile {
  id: string;
  name: string;
  size: number;
  status: 'pending' | 'converting' | 'completed' | 'error';
  progress: number;
  uploadedAt: Date;
}

// 转换参数
export interface ConvertParams {
  arcHeight: number;
  wireDiameter: number;
  material: string;
  outputFormat: string;
}

// 转换任务（新界面用）
export interface ConvertTask {
  id: string;
  file: DXFFile;
  params: ConvertParams;
  status: 'queued' | 'processing' | 'completed' | 'error';
  progress: number;
  createdAt: Date;
}

// DRC 结果
export interface DRCResult {
  id: string;
  severity: 'error' | 'warning' | 'info';
  message: string;
  location?: {
    x: number;
    y: number;
  };
}

// 焊点坐标
export interface BondingCoordinate {
  x: number;
  y: number;
  z: number;
  type: 'ball' | 'wedge' | 'stitch';
  index: number;
}


// ========== IGBT 特定类型 ==========

// IGBT 焊盘类型
export type IGBTPadType = 'emitter' | 'collector' | 'gate' | 'sense' | 'dummy'

// IGBT 引线类型
export type IGBTWireType = 'al_wire' | 'al_ribbon' | 'cu_wire' | 'au_wire'

// IGBT 模式
export type IGBTMode = 'standard' | 'igbt' | 'automotive'

// IGBT 规则配置
export interface IGBTRules {
  modes: Array<{
    id: IGBTMode
    name: string
    description: string
  }>
  voltage_classes: Array<{
    class: 'low' | 'medium' | 'high' | 'ultra_high'
    name: string
    range: string
    min_spacing: number
  }>
  wire_types: Array<{
    id: IGBTWireType
    name: string
    diameters?: number[]
    sizes?: string[]
  }>
  pad_types: Array<{
    id: IGBTPadType
    name: string
    min_size: number
    description: string
  }>
  current_density: Record<string, number>
}

// IGBT 焊盘信息
export interface IGBTPad {
  type: IGBTPadType
  x: number
  y: number
  width: number
  height: number
  net: string  // 网络名称
}

// IGBT 引线信息
export interface IGBTWire {
  from_pad: number  // 起始焊盘索引
  to_pad: number    // 目标焊盘索引
  wire_type: IGBTWireType
  diameter: number
  expected_current: number
}

// IGBT 设计信息
export interface IGBTDesign {
  operating_voltage: number
  max_current: number
  ambient_temperature: number
  package_type: string  // TO-247, TO-220, etc.
}
