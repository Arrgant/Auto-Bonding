import { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { BondingCoordinate } from '@/types';

interface ThreeViewerProps {
  coordinates: BondingCoordinate[];
}

export function ThreeViewer({ coordinates }: ThreeViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<any>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    // 创建场景
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0f172a);
    sceneRef.current = scene;

    // 创建相机
    const camera = new THREE.PerspectiveCamera(
      75,
      containerRef.current.clientWidth / containerRef.current.clientHeight,
      0.1,
      1000
    );
    camera.position.set(5, 5, 5);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    // 创建渲染器
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 添加轨道控制
    import('three/examples/jsm/controls/OrbitControls.js').then(({ OrbitControls }) => {
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controlsRef.current = controls;
    });

    // 添加网格
    const gridHelper = new THREE.GridHelper(10, 10, 0x475569, 0x1e293b);
    scene.add(gridHelper);

    // 添加坐标轴
    const axesHelper = new THREE.AxesHelper(2);
    scene.add(axesHelper);

    // 添加光源
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
    scene.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 5, 5);
    scene.add(directionalLight);

    // 动画循环
    let animationId: number;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      if (controlsRef.current) {
        controlsRef.current.update();
      }
      renderer.render(scene, camera);
    };
    animate();

    // 窗口大小调整
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current || !rendererRef.current) return;
      cameraRef.current.aspect = containerRef.current.clientWidth / containerRef.current.clientHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(containerRef.current.clientWidth, containerRef.current.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      cancelAnimationFrame(animationId);
      if (containerRef.current && renderer.domElement) {
        containerRef.current.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  // 更新坐标点
  useEffect(() => {
    if (!sceneRef.current || coordinates.length === 0) return;

    // 清除旧的点
    sceneRef.current.children
      .filter((child) => child.userData.isBondingPoint)
      .forEach((child) => sceneRef.current!.remove(child));

    // 添加新的点
    coordinates.forEach((coord, index) => {
      const geometry = new THREE.SphereGeometry(0.08, 16, 16);
      const color = coord.type === 'ball' ? 0xfbbf24 : coord.type === 'wedge' ? 0x3b82f6 : 0x10b981;
      const material = new THREE.MeshStandardMaterial({ color, metalness: 0.8, roughness: 0.2 });
      const sphere = new THREE.Mesh(geometry, material);
      sphere.position.set(coord.x, coord.y, coord.z);
      sphere.userData = { isBondingPoint: true, index };
      sceneRef.current!.add(sphere);

      // 添加标签
      // （简化版本，省略标签）
    });

    // 添加连线（模拟线弧）
    if (coordinates.length > 1) {
      const points = coordinates.map((c) => new THREE.Vector3(c.x, c.y, c.z));
      const curve = new THREE.CatmullRomCurve3(points);
      const tubeGeometry = new THREE.TubeGeometry(curve, 100, 0.02, 8, false);
      const tubeMaterial = new THREE.MeshStandardMaterial({ 
        color: 0xfbbf24, 
        metalness: 0.9, 
        roughness: 0.1,
        transparent: true,
        opacity: 0.8
      });
      const tube = new THREE.Mesh(tubeGeometry, tubeMaterial);
      tube.userData = { isBondingWire: true };
      sceneRef.current!.add(tube);
    }
  }, [coordinates]);

  return (
    <div ref={containerRef} className="w-full h-full">
      {coordinates.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-muted-foreground">
            <div className="text-4xl mb-3">🎯</div>
            <div className="text-lg font-medium">3D 预览区</div>
            <div className="text-sm">上传文件并转换后查看焊点坐标</div>
          </div>
        </div>
      )}
    </div>
  );
}
