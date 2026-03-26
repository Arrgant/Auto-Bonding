import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import DXFParser from 'dxf-parser';

interface DXFEntity {
  type: string;
  layer: string;
  vertices?: { x: number; y: number }[];
  center?: { x: number; y: number };
  radius?: number;
  start?: { x: number; y: number };
  end?: { x: number; y: number };
}

interface DXF2DViewerProps {
  dxfFile?: File | null;
  onDXFLoaded?: (entities: DXFEntity[], bounds: { minX: number; maxX: number; minY: number; maxY: number }) => void;
}

export function DXF2DViewer({ dxfFile, onDXFLoaded }: DXF2DViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.OrthographicCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 初始化 Three.js 场景
  useEffect(() => {
    if (!containerRef.current) return;

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xffffff);
    sceneRef.current = scene;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight;
    const frustumSize = 100;
    
    const camera = new THREE.OrthographicCamera(
      -frustumSize * (width / height) / 2,
      frustumSize * (width / height) / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      1000
    );
    camera.position.set(0, 0, 10);
    camera.lookAt(0, 0, 0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(window.devicePixelRatio);
    containerRef.current.appendChild(renderer.domElement);
    rendererRef.current = renderer;

    // 添加光源
    const ambientLight = new THREE.AmbientLight(0xffffff, 1);
    scene.add(ambientLight);

    // 动画循环
    let animationId: number;
    const animate = () => {
      animationId = requestAnimationFrame(animate);
      renderer.render(scene, camera);
    };
    animate();

    // 窗口大小调整
    const handleResize = () => {
      if (!containerRef.current || !cameraRef.current || !rendererRef.current) return;
      const newWidth = containerRef.current.clientWidth;
      const newHeight = containerRef.current.clientHeight;
      const aspect = newWidth / newHeight;
      
      cameraRef.current.left = -frustumSize * aspect / 2;
      cameraRef.current.right = frustumSize * aspect / 2;
      cameraRef.current.top = frustumSize / 2;
      cameraRef.current.bottom = -frustumSize / 2;
      cameraRef.current.updateProjectionMatrix();
      
      rendererRef.current.setSize(newWidth, newHeight);
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

  // 解析并渲染 DXF
  useEffect(() => {
    if (!dxfFile || !sceneRef.current) return;

    const parseAndRender = async () => {
      setLoading(true);
      setError(null);

      try {
        const text = await dxfFile.text();
        const parser = new DXFParser();
        const dxf = parser.parse(text);

        if (!dxf || !dxf.entities) {
          throw new Error('无效的 DXF 文件');
        }

        // 清除旧的实体
        sceneRef.current!.children
          .filter((child) => child.userData.isDXFEntity)
          .forEach((child) => sceneRef.current!.remove(child));

        const entities: DXFEntity[] = [];
        let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

        // 渲染不同的 DXF 实体
        dxf.entities.forEach((entity: any) => {
          const dxfEntity: DXFEntity = {
            type: entity.type,
            layer: entity.layer || '0',
          };

          let color = 0x000000;
          if (entity.color && typeof entity.color === 'number') {
            color = entity.color;
          }

          if (entity.type === 'LINE' && entity.vertices) {
            dxfEntity.vertices = entity.vertices.map((v: any) => ({ x: v.x, y: v.y }));
            const points = entity.vertices.map((v: any) => new THREE.Vector3(v.x, v.y, 0));
            const geometry = new THREE.BufferGeometry().setFromPoints(points);
            const material = new THREE.LineBasicMaterial({ color });
            const line = new THREE.Line(geometry, material);
            line.userData = { isDXFEntity: true };
            sceneRef.current!.add(line);

            entity.vertices.forEach((v: any) => {
              minX = Math.min(minX, v.x);
              maxX = Math.max(maxX, v.x);
              minY = Math.min(minY, v.y);
              maxY = Math.max(maxY, v.y);
            });
          } else if (entity.type === 'CIRCLE' && entity.center && entity.radius) {
            dxfEntity.center = { x: entity.center.x, y: entity.center.y };
            dxfEntity.radius = entity.radius;
            
            const curve = new THREE.EllipseCurve(
              entity.center.x,
              entity.center.y,
              entity.radius,
              entity.radius,
              0,
              2 * Math.PI,
              false,
              0
            );
            const points = curve.getPoints(100);
            const geometry = new THREE.BufferGeometry().setFromPoints(
              points.map((p) => new THREE.Vector3(p.x, p.y, 0))
            );
            const material = new THREE.LineBasicMaterial({ color });
            const circle = new THREE.Line(geometry, material);
            circle.userData = { isDXFEntity: true };
            sceneRef.current!.add(circle);

            minX = Math.min(minX, entity.center.x - entity.radius);
            maxX = Math.max(maxX, entity.center.x + entity.radius);
            minY = Math.min(minY, entity.center.y - entity.radius);
            maxY = Math.max(maxY, entity.center.y + entity.radius);
          } else if (entity.type === 'POLYLINE' || entity.type === 'LWPOLYLINE') {
            if (entity.vertices) {
              dxfEntity.vertices = entity.vertices.map((v: any) => ({ x: v.x, y: v.y }));
              const points = entity.vertices.map((v: any) => new THREE.Vector3(v.x, v.y, 0));
              
              if (entity.closed) {
                points.push(points[0].clone());
              }
              
              const geometry = new THREE.BufferGeometry().setFromPoints(points);
              const material = new THREE.LineBasicMaterial({ color });
              const polyline = new THREE.Line(geometry, material);
              polyline.userData = { isDXFEntity: true };
              sceneRef.current!.add(polyline);

              entity.vertices.forEach((v: any) => {
                minX = Math.min(minX, v.x);
                maxX = Math.max(maxX, v.x);
                minY = Math.min(minY, v.y);
                maxY = Math.max(maxY, v.y);
              });
            }
          }

          entities.push(dxfEntity);
        });

        // 添加网格背景
        const gridSize = Math.max(maxX - minX, maxY - minY) * 1.5 || 100;
        const gridHelper = new THREE.GridHelper(gridSize, gridSize / 10, 0xcccccc, 0xeeeeee);
        gridHelper.rotation.x = Math.PI / 2;
        gridHelper.position.z = -0.1;
        gridHelper.userData = { isGrid: true };
        sceneRef.current!.add(gridHelper);

        // 调整相机以适合内容
        if (cameraRef.current && isFinite(minX) && isFinite(maxX)) {
          const padding = 1.2;
          const width = (maxX - minX) * padding;
          const height = (maxY - minY) * padding;
          const centerX = (minX + maxX) / 2;
          const centerY = (minY + maxY) / 2;
          
          const frustumSize = Math.max(width, height);
          const aspect = containerRef.current!.clientWidth / containerRef.current!.clientHeight;
          
          cameraRef.current.left = -frustumSize * aspect / 2;
          cameraRef.current.right = frustumSize * aspect / 2;
          cameraRef.current.top = frustumSize / 2;
          cameraRef.current.bottom = -frustumSize / 2;
          cameraRef.current.position.set(centerX, centerY, 10);
          cameraRef.current.updateProjectionMatrix();
        }

        onDXFLoaded?.(entities, { minX, maxX, minY, maxY });
      } catch (err) {
        setError(err instanceof Error ? err.message : '解析失败');
      } finally {
        setLoading(false);
      }
    };

    parseAndRender();
  }, [dxfFile, onDXFLoaded]);

  return (
    <div ref={containerRef} className="w-full h-full relative">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 pointer-events-none">
          <div className="text-center">
            <div className="text-2xl mb-2">⏳</div>
            <div className="text-sm text-muted-foreground">正在解析 DXF...</div>
          </div>
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center bg-white/80 pointer-events-none">
          <div className="text-center text-red-500">
            <div className="text-2xl mb-2">❌</div>
            <div className="text-sm">{error}</div>
          </div>
        </div>
      )}
      {!dxfFile && !loading && !error && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <div className="text-center text-muted-foreground">
            <div className="text-4xl mb-3">📐</div>
            <div className="text-lg font-medium">2D 视图</div>
            <div className="text-sm">上传 DXF 文件查看二维图纸</div>
          </div>
        </div>
      )}
    </div>
  );
}
