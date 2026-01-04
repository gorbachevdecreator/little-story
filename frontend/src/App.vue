<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

// --- СОСТОЯНИЕ (STATE) ---
const currentView = ref('menu') // 'menu' | 'story_profile' | 'game'
const loading = ref(false)

const library = ref([])
const userProfile = ref({ hearts: 0, max_hearts: 3, next_heart_in: 0 })
const selectedStoryManifest = ref(null)

const story = ref(null)
const currentSceneId = ref('')
const stepIndex = ref(0)
const gameState = ref({})

let timerInterval = null

// --- ТАЙМЕРЫ И ВЫЧИСЛЕНИЯ ---
const formattedTimer = computed(() => {
  const s = userProfile.value.next_heart_in
  if (s <= 0) return 'Full'
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const sec = Math.floor(s % 60)
  return `${h}:${m.toString().padStart(2, '0')}:${sec.toString().padStart(2, '0')}`
})

const currentScene = computed(() => story.value?.scenes[currentSceneId.value])
const currentStep = computed(() => currentScene.value?.flow[stepIndex.value])
const currentBackground = computed(() => currentScene.value ? `url('${currentScene.value.background}')` : '#222')

// --- ЗАПУСК ---
onMounted(async () => {
  await loadLibrary()
  await refreshUserProfile()
  timerInterval = setInterval(() => { 
    if(userProfile.value.next_heart_in > 0) userProfile.value.next_heart_in-- 
  }, 1000)
})

onUnmounted(() => { if(timerInterval) clearInterval(timerInterval) })

// --- API ЗАПРОСЫ ---

const loadLibrary = async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/library')
    library.value = await res.json()
  } catch (e) { console.error(e) }
}

const refreshUserProfile = async () => {
  try {
    const res = await fetch('http://127.0.0.1:8000/api/user')
    userProfile.value = await res.json()
  } catch(e) {}
}

// НОВОЕ: Функция сброса сердец (Debug)
const resetHearts = async () => {
  try {
    await fetch('http://127.0.0.1:8000/api/debug/reset_hearts', { method: 'POST' })
    await refreshUserProfile()
    alert("Сердца восстановлены до максимума!")
  } catch (e) {
    alert("Ошибка сброса: " + e)
  }
}

// НОВОЕ: Сохранение прогресса
const saveProgress = async () => {
  if (!selectedStoryManifest.value) return
  const storyId = selectedStoryManifest.value.id
  try {
    await fetch(`http://127.0.0.1:8000/api/story/${storyId}/save`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(gameState.value)
    })
    console.log("Сохранено на сервере")
  } catch (e) {
    console.error("Ошибка сохранения:", e)
  }
}

// --- ЛОГИКА ИНТЕРФЕЙСА ---

const openStoryProfile = async (storyId) => {
  try {
    loading.value = true
    const res = await fetch(`http://127.0.0.1:8000/api/story/${storyId}/manifest`)
    selectedStoryManifest.value = await res.json()
    currentView.value = 'story_profile'
  } catch(e) { console.error(e) } 
  finally { loading.value = false }
}

const playEpisode = async (episodeId) => {
  if (userProfile.value.hearts <= 0) {
    alert("У вас закончились сердца! 💔\nНажмите 'Восстановить' в меню.")
    return
  }
  
  try {
    loading.value = true
    const storyId = selectedStoryManifest.value.id
    
    // Делаем запрос
    const res = await fetch(`http://127.0.0.1:8000/api/story/${storyId}/${episodeId}/start`, { method: 'POST' })
    
    // Если ошибка - читаем текст ошибки от сервера!
    if (!res.ok) {
      const errData = await res.json()
      throw new Error(errData.detail || "Неизвестная ошибка сервера")
    }
    
    const data = await res.json()
    
    // Запускаем игру
    story.value = data
    currentSceneId.value = data.start_scene
    gameState.value = { ...data.initial_state }
    stepIndex.value = 0
    
    currentView.value = 'game'
    await refreshUserProfile()
    
  } catch(e) {
    // Теперь тут будет выводиться реальная причина (например "Episode file missing")
    alert("Не удалось запустить серию:\n" + e.message)
  } finally {
    loading.value = false
  }
}

const goHome = () => { currentView.value = 'menu'; selectedStoryManifest.value = null; }
const goBackToProfile = () => { currentView.value = 'story_profile'; story.value = null; }

// --- ИГРОВАЯ ЛОГИКА ---

const next = () => {
  if (!currentStep.value || currentStep.value.type === 'choice') return
  if (stepIndex.value < currentScene.value.flow.length - 1) stepIndex.value++
}

const checkCondition = (opt) => {
  // 1. Если это уникальный выбор и он уже был сделан -> Кнопка всегда доступна
  if (opt.unique_id && gameState.value[opt.unique_id]) {
    return true
  }

  // 2. Стандартная проверка
  if (!opt.conditions) return true
  for (const [key, req] of Object.entries(opt.conditions)) {
    if ((gameState.value[key] || 0) < req) return false
  }
  return true
}

// ИСПРАВЛЕННАЯ ФУНКЦИЯ ВЫБОРА (Она теперь одна!)
const makeChoice = async (option) => {
  // Проверяем: Был ли этот выбор уже куплен?
  const isAlreadyPurchased = option.unique_id && gameState.value[option.unique_id]

  // 1. Применяем эффекты ТОЛЬКО если это первая покупка
  if (!isAlreadyPurchased && option.effects) {
    for (const [key, change] of Object.entries(option.effects)) {
      gameState.value[key] = (gameState.value[key] || 0) + change
    }
    
    // Если есть unique_id, запоминаем, что мы это купили
    if (option.unique_id) {
      gameState.value[option.unique_id] = true
    }

    // Сохраняем изменения
    await saveProgress()
  }

  // 2. Переходим к сцене
  if (option.next_scene) {
    currentSceneId.value = option.next_scene
    stepIndex.value = 0
  }
}
</script>

<template>
  <div class="app-container">
    
    <div v-if="currentView !== 'game'" class="top-bar">
      <div class="hearts-display">❤️ {{ userProfile.hearts }} <span v-if="userProfile.hearts < userProfile.max_hearts" class="timer">({{ formattedTimer }})</span></div>
    </div>

    <div v-if="currentView === 'menu'" class="screen menu-screen">
      <h1 class="app-title">Little Story</h1>
      
      <button class="debug-btn" @click="resetHearts">🔄 Восстановить сердца (Debug)</button>
      
      <div v-if="loading">Загрузка...</div>
      <div class="library-grid">
        <div v-for="item in library" :key="item.id" class="story-card" @click="openStoryProfile(item.id)">
          <img :src="item.cover" class="cover-img" />
          <div class="card-title">{{ item.title }}</div>
        </div>
      </div>
    </div>

    <div v-else-if="currentView === 'story_profile'" class="screen profile-screen">
      <button class="back-btn-ui" @click="goHome">← Меню</button>
      
      <div v-if="selectedStoryManifest" class="manifest-content">
        <img :src="selectedStoryManifest.cover" class="profile-cover" />
        <h2>{{ selectedStoryManifest.title }}</h2>
        <p class="description">{{ selectedStoryManifest.description }}</p>
        
        <div class="seasons-list">
          <div v-for="season in selectedStoryManifest.seasons" :key="season.id" class="season-block">
            <h3>{{ season.title }}</h3>
            <div class="episodes-list">
              <div v-for="ep in season.episodes" :key="ep.id" class="episode-row">
                <span>{{ ep.title }}</span>
                <button class="play-btn" @click="playEpisode(ep.id)">Играть</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="currentView === 'game'" class="game-screen" :style="{ backgroundImage: currentBackground }" @click="next">
      <button class="back-btn-game" @click.stop="goBackToProfile">🚪</button>
      
      <div class="hud"><div v-for="(v, k) in gameState" :key="k" class="hud-item">{{k}}: {{v}}</div></div>
      
      <transition name="fade"><img v-if="currentStep?.sprite" :src="currentStep.sprite" class="character-sprite" /></transition>
      
      <div v-if="currentStep?.type === 'say'" class="dialog-box">
        <div class="name-tag">{{ currentStep.character }}</div>
        <div class="text-content">{{ currentStep.text }}</div>
      </div>
      
      <div v-if="currentStep?.type === 'choice'" class="choice-container">
        <div class="choice-title">{{ currentStep.text }}</div>
        <button 
  v-for="opt in currentStep.options" 
  :key="opt.text" 
  class="choice-btn"
  :class="{ 'disabled': !checkCondition(opt) }" 
  :disabled="!checkCondition(opt)" 
  @click.stop="makeChoice(opt)"
>
  {{ opt.text }}
  
  <span v-if="opt.unique_id && gameState[opt.unique_id]" class="purchased-tag">
    (Куплено ✅)
  </span>
  
  <span v-else-if="opt.conditions?.gold" class="price-tag">
    ({{ opt.conditions.gold }} 💰)
  </span>
</button>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* Стили */
.app-container { font-family: 'Segoe UI', sans-serif; color: white; background: #1a1a1a; min-height: 100vh; }
.top-bar { background: #2a2a2a; padding: 10px; display: flex; justify-content: flex-end; }
.hearts-display { background: #444; padding: 5px 15px; border-radius: 20px; font-weight: bold; }
.timer { font-size: 0.8em; color: #aaa; margin-left: 5px; }

.screen { padding: 20px; text-align: center; max-width: 600px; margin: 0 auto; }
.app-title { color: #ffd700; margin-bottom: 10px; }
.debug-btn { background: #444; color: #aaa; border: 1px dashed #666; padding: 5px 10px; cursor: pointer; margin-bottom: 20px; font-size: 0.8em; }

.library-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 15px; }
.story-card { background: #333; border-radius: 10px; overflow: hidden; cursor: pointer; }
.cover-img { width: 100%; height: 200px; object-fit: cover; }
.card-title { padding: 10px; font-weight: bold; }

/* Profile */
.profile-cover { width: 150px; border-radius: 10px; margin-bottom: 10px; }
.episode-row { display: flex; justify-content: space-between; align-items: center; background: #333; padding: 10px; margin-bottom: 5px; border-radius: 8px; }
.play-btn { background: #e056fd; border: none; color: white; padding: 5px 10px; border-radius: 5px; cursor: pointer; font-weight: bold; }
.back-btn-ui { background: transparent; border: 1px solid #555; color: white; padding: 5px 15px; margin-bottom: 20px; cursor: pointer; }

/* Game */
.game-screen { width: 100vw; height: 100vh; max-width: 480px; margin: 0 auto; background-size: cover; background-position: center; position: relative; display: flex; flex-direction: column; justify-content: flex-end; overflow: hidden; }
.back-btn-game { position: absolute; top: 10px; right: 10px; z-index: 100; background: rgba(0,0,0,0.5); border: none; font-size: 1.5em; cursor: pointer; border-radius: 50%; width: 40px; height: 40px; }
.hud { position: absolute; top: 10px; left: 10px; display: flex; gap: 10px; z-index: 50; }
.hud-item { background: rgba(0,0,0,0.6); padding: 5px 10px; border-radius: 10px; }
.character-sprite { position: absolute; bottom: 0; left: 50%; transform: translateX(-50%); height: 80%; object-fit: contain; pointer-events: none; z-index: 1; }
.dialog-box { background: rgba(0,0,0,0.85); padding: 20px; margin: 20px; border-radius: 15px; border: 2px solid #555; position: relative; z-index: 10; }
.name-tag { color: #ffd700; font-weight: bold; margin-bottom: 5px; }
.choice-container { position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 15px; z-index: 20; }
.choice-btn { background: linear-gradient(to right, #6a11cb, #2575fc); color: white; border: none; padding: 15px 30px; border-radius: 30px; width: 80%; }
.choice-btn.disabled { background: #555; opacity: 0.5; }
.purchased-tag { font-size: 0.8em; color: #76ff03; margin-left: 5px; }
</style>