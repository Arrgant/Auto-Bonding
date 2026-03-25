// 材料类型
export interface Material {
  id: string;
  name: string;
  coefficient: number;
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
  type: 'spacing' | 'height' | 'width';
  severity: 'error' | 'warning';
  description: string;
  actual_value: number;
  required_value: number;
  location?: {
    x: number;
    y: number;
    z: number;
  };
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
