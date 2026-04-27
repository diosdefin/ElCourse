<template>
  <div class="w-full h-[400px] relative" ref="containerRef"></div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'

const containerRef = ref(null)

let scene, camera, renderer, model, mixer, animationId, pivotGroup
let isDragging = false
let lastMouseX = 0
let lastMouseY = 0
let targetRotationY = 0
let targetRotationX = 0
let currentRotationY = 0
let currentRotationX = 0

// Автовращение
let autoRotateSpeed = 0.005
let autoRotateEnabled = true

onMounted(() => {
  const container = containerRef.value
  if (!container) return

  scene = new THREE.Scene()
  scene.background = null
  
  // КАМЕРА
  camera = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 0.01, 1000)
  camera.position.set(0, 1, 4.2)
  camera.lookAt(0, 0, 0)

  // РЕНДЕР С МАКСИМАЛЬНЫМ КАЧЕСТВОМ
  renderer = new THREE.WebGLRenderer({ 
    alpha: true, 
    antialias: true,
    powerPreference: "high-performance"
  })
  renderer.setPixelRatio(window.devicePixelRatio)  // ← высокое разрешение
  renderer.setSize(container.clientWidth, container.clientHeight)
  renderer.setClearColor(0x000000, 0)
  renderer.toneMapping = THREE.ACESFilmicToneMapping  // ← кинематографические цвета
  renderer.toneMappingExposure = 1.2
  renderer.shadowMap.enabled = true
  renderer.shadowMap.type = THREE.PCFSoftShadowMap
  container.appendChild(renderer.domElement)

  // ОСВЕЩЕНИЕ (улучшенное)
  const ambientLight = new THREE.AmbientLight(0x404060, 0.6)
  scene.add(ambientLight)
  
  const mainLight = new THREE.DirectionalLight(0xffaa88, 1.5)
  mainLight.position.set(3, 5, 2)
  mainLight.castShadow = true
  mainLight.shadow.mapSize.width = 1024
  mainLight.shadow.mapSize.height = 1024
  scene.add(mainLight)
  
  const fillLight = new THREE.DirectionalLight(0x88aaff, 0.8)
  fillLight.position.set(-2, 3, 4)
  scene.add(fillLight)
  
  // Добавляем контровой свет для объёма
  const backLight = new THREE.PointLight(0xff6633, 0.5)
  backLight.position.set(0, 1, -3)
  scene.add(backLight)

  // ЗАГРУЗКА МОДЕЛИ
  const loader = new GLTFLoader()
  console.log('📁 Загрузка модели...')
  
  loader.load('/models/phoenix.glb', 
    (gltf) => {
      console.log('✅ Модель загружена!')
      model = gltf.scene
      
      // МАСШТАБ
      model.scale.set(0.526, 0.526, 0.526)
      
      // ПЕРЕНЕСЕНИЕ ЦЕНТРА
      const box = new THREE.Box3().setFromObject(model)
      const center = box.getCenter(new THREE.Vector3())
      
      pivotGroup = new THREE.Group()
      pivotGroup.add(model)
      scene.add(pivotGroup)
      
      // Смещаем модель внутри группы
      model.position.set(-center.x, -center.y, -center.z)
      
      // Финальная позиция группы (чуть выше)
      pivotGroup.position.set(0, 0, 0)
      pivotGroup.rotation.y = -1.57
      
      // Сохраняем текущее вращение для автовращения
      currentRotationY = pivotGroup.rotation.y
      targetRotationY = currentRotationY
      
      // УЛУЧШЕННЫЕ МАТЕРИАЛЫ
      model.traverse((child) => {
        if (child.isMesh && child.material) {
          child.material.roughness = 0.4
          child.material.metalness = 0.3
          child.castShadow = true
          child.receiveShadow = false
        }
      })
      
      // Анимация модели
      if (gltf.animations && gltf.animations.length) {
        mixer = new THREE.AnimationMixer(model)
        mixer.clipAction(gltf.animations[0]).play()
        console.log('🎬 Анимация запущена')
      }
    },
    undefined,
    (error) => console.error('❌ Ошибка:', error)
  )

  // ========== УПРАВЛЕНИЕ МЫШКОЙ ==========
  const onMouseDown = (e) => {
    isDragging = true
    lastMouseX = e.clientX
    lastMouseY = e.clientY
    autoRotateEnabled = false
    container.style.cursor = 'grabbing'
  }
  
  const onMouseMove = (e) => {
    if (!isDragging || !pivotGroup) return
    
    const deltaX = e.clientX - lastMouseX
    const deltaY = e.clientY - lastMouseY
    
    targetRotationY += deltaX * 0.008
    targetRotationX += deltaY * 0.008
    targetRotationX = Math.max(-1, Math.min(1, targetRotationX))
    
    lastMouseX = e.clientX
    lastMouseY = e.clientY
  }
  
  const onMouseUp = () => {
    if (isDragging) {
      isDragging = false
      container.style.cursor = 'grab'
      setTimeout(() => {
        if (!isDragging) {
          autoRotateEnabled = true
        }
      }, 1000)
    }
  }
  
  container.addEventListener('mousedown', onMouseDown)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  container.style.cursor = 'grab'

  // АНИМАЦИЯ
  let time = 0
  function animate() {
    animationId = requestAnimationFrame(animate)
    time += 0.016
    
    if (mixer) mixer.update(0.016)
    
    if (pivotGroup) {
      if (autoRotateEnabled && !isDragging) {
        targetRotationY += autoRotateSpeed
      }
      
      currentRotationY += (targetRotationY - currentRotationY) * 0.08
      currentRotationX += (targetRotationX - currentRotationX) * 0.08
      
      pivotGroup.rotation.y = currentRotationY
      pivotGroup.rotation.x = currentRotationX
      
      // Лёгкое парение
      pivotGroup.position.y = 0 + Math.sin(time * 1.5) * 0.03
    }
    
    renderer.render(scene, camera)
  }
  animate()
  
  onUnmounted(() => {
    container.removeEventListener('mousedown', onMouseDown)
    window.removeEventListener('mousemove', onMouseMove)
    window.removeEventListener('mouseup', onMouseUp)
    if (animationId) cancelAnimationFrame(animationId)
    if (mixer) mixer?.stopAllAction()
    if (renderer) renderer.dispose()
  })
})

function handleResize() {
  if (!containerRef.value) return
  const container = containerRef.value
  camera.aspect = container.clientWidth / container.clientHeight
  camera.updateProjectionMatrix()
  renderer.setSize(container.clientWidth, container.clientHeight)
}

window.addEventListener('resize', handleResize)

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>