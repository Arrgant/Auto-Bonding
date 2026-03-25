import { Canvas } from '@react-three/fiber'
import { OrbitControls, Grid, Environment, Stats } from '@react-three/drei'
import { Suspense, useState } from 'react'

export default function ModelViewer3D() {
  const [wireframe, setWireframe] = useState(false)

  return (
    <div className="h-full flex flex-col">
      {/* 工具栏 */}
      <div className="flex items-center justify-between p-4 border-b border-dark-border">
        <h3 className="text-lg font-semibold text-white">3D 预览</h3>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setWireframe(!wireframe)}
            className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
              wireframe
                ? 'bg-primary-600 text-white'
                : 'bg-dark-border text-gray-300 hover:bg-dark-bg'
            }`}
          >
            线框模式
          </button>
          <button className="px-3 py-1.5 bg-dark-border text-gray-300 rounded-lg text-sm hover:bg-dark-bg transition-colors">
            适应窗口
          </button>
        </div>
      </div>

      {/* 3D 画布 */}
      <div className="flex-1 bg-dark-bg relative">
        <Canvas
          camera={{ position: [10, 10, 10], fov: 50 }}
          shadows
          dpr={[1, 2]}
        >
          <Suspense fallback={null}>
            {/* 光照 */}
            <ambientLight intensity={0.5} />
            <directionalLight position={[10, 10, 5]} intensity={1} castShadow />
            <pointLight position={[-10, -10, -5]} intensity={0.5} />

            {/* 环境 */}
            <Environment preset="city" />

            {/* 网格 */}
            <Grid
              position={[0, -2, 0]}
              args={[20, 20]}
              cellColor="#475569"
              sectionColor="#64748b"
              fadeDistance={30}
              fadeStrength={1}
            />

            {/* 示例模型 - 临时显示 */}
            <ExampleModel wireframe={wireframe} />

            {/* 相机控制 */}
            <OrbitControls
              enableDamping
              dampingFactor={0.05}
              screenSpacePanning={false}
              minDistance={2}
              maxDistance={100}
            />

            {/* 性能统计 */}
            <Stats className="!top-auto !bottom-2 !left-2 !right-auto" />
          </Suspense>
        </Canvas>

        {/* 空状态提示 */}
        <div className="absolute top-4 left-4 bg-dark-card/80 backdrop-blur rounded-lg px-4 py-2 text-sm text-gray-400">
          📭 暂无模型，请上传 DXF 文件并转换
        </div>

        {/* 操作提示 */}
        <div className="absolute bottom-4 right-4 bg-dark-card/80 backdrop-blur rounded-lg px-4 py-2 text-xs text-gray-500">
          左键旋转 · 右键平移 · 滚轮缩放
        </div>
      </div>
    </div>
  )
}

// 示例模型（临时）
function ExampleModel({ wireframe }: { wireframe: boolean }) {
  return (
    <group position={[0, -1, 0]}>
      {/* 焊盘 */}
      <mesh position={[-2, 0, 0]} castShadow>
        <boxGeometry args={[2, 0.1, 2]} />
        <meshStandardMaterial
          color="#3b82f6"
          metalness={0.8}
          roughness={0.2}
          wireframe={wireframe}
        />
      </mesh>

      {/* 引线弧 */}
      <mesh position={[0, 0.5, 0]} castShadow>
        <torusGeometry args={[2, 0.05, 16, 100, Math.PI]} />
        <meshStandardMaterial
          color="#fbbf24"
          metalness={0.9}
          roughness={0.1}
          wireframe={wireframe}
        />
      </mesh>

      {/* 引线框架 */}
      <mesh position={[2, 0, 0]} castShadow>
        <boxGeometry args={[3, 0.1, 0.5]} />
        <meshStandardMaterial
          color="#94a3b8"
          metalness={0.7}
          roughness={0.3}
          wireframe={wireframe}
        />
      </mesh>
    </group>
  )
}
