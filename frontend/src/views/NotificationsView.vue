<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const offers = ref([])
const loading = ref(true)
const selectedOffer = ref(null)
const showConfirmModal = ref(false)
const confirmAction = ref(null) // 'accepted' или 'rejected'

const fetchOffers = async () => {
  try {
    const token = localStorage.getItem('access_token')
    const url = authStore.isStudent 
      ? 'http://127.0.0.1:8000/api/student/offers/' 
      : 'http://127.0.0.1:8000/api/employer/offers/'
    
    const res = await axios.get(url, { headers: { Authorization: `Bearer ${token}` } })
    offers.value = res.data
  } catch (e) { 
    console.error('Ошибка загрузки офферов:', e) 
  } finally { 
    loading.value = false 
  }
}

const openOffer = async (offer) => {
  selectedOffer.value = offer
  const token = localStorage.getItem('access_token')
  let isUpdated = false

  // Логика прочтения для студента
  if (authStore.isStudent && !offer.is_read_by_student) {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/offers/${offer.id}/update/`, 
        { is_read_by_student: true }, 
        { headers: { Authorization: `Bearer ${token}` } }
      )
      isUpdated = true
    } catch (e) { console.error(e) }
  } 
  // Логика прочтения для работодателя
  else if (authStore.isEmployer && !offer.is_read_by_employer) {
    try {
      await axios.patch(`http://127.0.0.1:8000/api/offers/${offer.id}/update/`, 
        { is_read_by_employer: true }, 
        { headers: { Authorization: `Bearer ${token}` } }
      )
      isUpdated = true
    } catch (e) { console.error(e) }
  }

  // ЕСЛИ СТАТУС ПОМЕНЯЛСЯ - ОБНОВЛЯЕМ ВСЁ МОМЕНТАЛЬНО
  if (isUpdated) {
    await fetchOffers() // Качаем свежий список (пропадет выделение цветом)
    selectedOffer.value = offers.value.find(o => o.id === offer.id) // Обновляем модальное окно
    window.dispatchEvent(new CustomEvent('update-bell')) // Дергаем колокольчик
  }
}

const handleAction = async () => {
  if (!selectedOffer.value) return
  
  try {
    const token = localStorage.getItem('access_token')
    await axios.patch(`http://127.0.0.1:8000/api/offers/${selectedOffer.value.id}/update/`, 
      { status: confirmAction.value },
      { headers: { Authorization: `Bearer ${token}` } }
    )
    
    showConfirmModal.value = false
    
    // МАГИЯ ОБНОВЛЕНИЯ: Качаем свежие данные с бэкенда
    await fetchOffers() 
    
    // Обновляем модальное окно новыми данными
    selectedOffer.value = offers.value.find(o => o.id === selectedOffer.value.id)
    
    window.dispatchEvent(new CustomEvent('update-bell')) // Дергаем колокольчик
  } catch (e) { 
    console.error('Ошибка при обновлении статуса:', e)
    alert('Не удалось обновить статус предложения')
  }
}

const getContactLink = (offer) => {
  const text = encodeURIComponent(`Здравствуйте! Я принял ваше приглашение на платформе ELCOURSE. Мой ник: ${offer.student_name}. Давайте обсудим детали.`)
  return offer.contact_link ? `${offer.contact_link}?text=${text}` : '#'
}

const unreadCount = computed(() => {
  if (authStore.isStudent) {
    return offers.value.filter(o => !o.is_read_by_student && o.status === 'pending').length
  }
  return offers.value.filter(o => !o.is_read_by_employer && o.status !== 'pending').length
})

onMounted(fetchOffers)
</script>

<template>
  <div class="max-w-4xl mx-auto mt-10 px-4">
    <h1 class="text-3xl font-black text-white mb-8 flex items-center gap-3">
      Уведомления
      <span v-if="unreadCount > 0" class="text-sm bg-rose-500 text-white px-3 py-1 rounded-full">
        {{ unreadCount }} новых
      </span>
    </h1>

    <div v-if="loading" class="text-slate-500 text-center py-20">
      <div class="animate-spin w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full mx-auto mb-4"></div>
      Загрузка...
    </div>
    
    <div v-else-if="offers.length === 0" class="text-slate-500 text-center py-20 border-2 border-dashed border-slate-800 rounded-3xl">
      📭 Здесь пока пусто
    </div>

    <div class="grid gap-4">
      <div 
        v-for="offer in offers" 
        :key="offer.id" 
        @click="openOffer(offer)"
        class="p-6 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group"
        :class="{
          /* НОВОЕ (Студент) */
          'bg-indigo-600/20 border-indigo-500 shadow-lg': !offer.is_read_by_student && authStore.isStudent,
          
          /* НОВОЕ (Работодатель) */
          'bg-emerald-600/20 border-emerald-500 shadow-lg': !offer.is_read_by_employer && authStore.isEmployer,
          
          /* ЗАБЫТОЕ (Прочитал, но не ответил) */
          'border-amber-500/50 bg-amber-500/5': offer.is_read_by_student && offer.status === 'pending' && authStore.isStudent,
          
          /* РЕШЕННОЕ (Тусклое и серое) */
          'bg-slate-800/20 border-slate-700/50 opacity-50 grayscale hover:opacity-100 hover:grayscale-0': offer.status !== 'pending' && ((authStore.isStudent && offer.is_read_by_student) || (authStore.isEmployer && offer.is_read_by_employer))
        }"
      >
        <div 
          v-if="offer.is_read_by_student && offer.status === 'pending' && authStore.isStudent" 
          class="absolute top-0 right-0 bg-amber-500 text-slate-950 text-[10px] font-black px-3 py-1 rounded-bl-xl uppercase z-10"
        >
          ⚡ Нужен ваш ответ
        </div>

        <div 
          v-if="(!offer.is_read_by_student && authStore.isStudent) || (!offer.is_read_by_employer && authStore.isEmployer)" 
          class="absolute top-0 left-0 bg-indigo-500 text-white text-[10px] font-black px-3 py-1 rounded-br-xl uppercase z-10"
        >
          🆕 Новое
        </div>

        <div class="flex justify-between items-start">
          <div class="flex items-center gap-4">
            <div class="w-12 h-12 rounded-xl bg-slate-700 flex items-center justify-center font-bold text-white text-lg">
              {{ authStore.isStudent ? offer.employer_name?.[0] || '?' : offer.student_name?.[0] || '?' }}
            </div>
            <div>
              <h3 class="font-bold text-slate-100">
                {{ authStore.isStudent ? `Приглашение от ${offer.employer_name}` : `Предложение для ${offer.student_name}` }}
              </h3>
              <p class="text-sm text-slate-400 mt-1 max-w-md">{{ offer.message.substring(0, 80) }}{{ offer.message.length > 80 ? '...' : '' }}</p>
            </div>
          </div>
          
          <div class="text-right ml-4">
            <div 
              v-if="offer.status !== 'pending'" 
              class="text-[10px] font-black px-3 py-1 rounded-full mb-2 inline-block transition-colors"
              :class="offer.status === 'accepted' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-rose-500/20 text-rose-400'"
            >
              {{ offer.status === 'accepted' ? '✓ Принято' : '✗ Отклонено' }}
            </div>
            <p class="text-[10px] text-slate-500 uppercase font-bold">{{ new Date(offer.created_at).toLocaleDateString() }}</p>
            <p class="text-[9px] text-slate-600 mt-1">{{ new Date(offer.created_at).toLocaleTimeString() }}</p>
          </div>
        </div>
      </div>
    </div>
    
    <div v-if="selectedOffer" class="fixed inset-0 z-[110] flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md" @click.self="selectedOffer = null">
      <div class="bg-slate-900 border border-slate-700 w-full max-w-lg rounded-3xl shadow-2xl p-8 animate-fade-in-up">
        <div class="flex justify-between items-start mb-4">
          <h2 class="text-2xl font-black text-white">Детали предложения</h2>
          <button @click="selectedOffer = null" class="text-slate-500 hover:text-white text-2xl">&times;</button>
        </div>
        
        <div class="space-y-4 mb-8">
          <div class="flex items-center gap-3 pb-3 border-b border-slate-700">
            <div class="w-10 h-10 rounded-full bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold">
              {{ authStore.isStudent ? selectedOffer.employer_name?.[0] : selectedOffer.student_name?.[0] }}
            </div>
            <div>
              <p class="text-slate-400 text-xs">{{ authStore.isStudent ? 'Отправитель (Работодатель)' : 'Кандидат (Студент)' }}</p>
              <p class="text-white font-bold">{{ authStore.isStudent ? selectedOffer.employer_name : selectedOffer.student_name }}</p>
            </div>
          </div>
          
          <div>
            <p class="text-slate-400 text-sm font-bold uppercase tracking-tighter mb-2">📝 Сообщение:</p>
            <div class="p-4 bg-slate-800/50 rounded-2xl border border-slate-700 text-slate-200 whitespace-pre-wrap">
              {{ selectedOffer.message || 'Нет текста сообщения' }}
            </div>
          </div>
          
          <div>
            <p class="text-slate-400 text-sm font-bold uppercase tracking-tighter mb-2">📅 Дата:</p>
            <p class="text-slate-300">{{ new Date(selectedOffer.created_at).toLocaleString() }}</p>
          </div>
          
          <div v-if="selectedOffer.status !== 'pending'">
            <p class="text-slate-400 text-sm font-bold uppercase tracking-tighter mb-2">⚡ Статус:</p>
            <p :class="selectedOffer.status === 'accepted' ? 'text-emerald-400' : 'text-rose-400'" class="font-bold">
              {{ selectedOffer.status === 'accepted' ? '✓ Принято' : '✗ Отклонено' }}
            </p>
          </div>
        </div>

        <div v-if="selectedOffer.status === 'pending' && authStore.isStudent" class="flex gap-3">
          <button @click="confirmAction = 'accepted'; showConfirmModal = true" 
            class="flex-1 py-4 bg-emerald-600 text-white font-bold rounded-2xl hover:bg-emerald-500 transition-all active:scale-95">
            ✅ Принять
          </button>
          
          <button @click="confirmAction = 'rejected'; showConfirmModal = true" 
            class="flex-1 py-4 bg-slate-800 text-slate-300 font-bold rounded-2xl hover:bg-rose-900/30 hover:text-rose-400 transition-all active:scale-95">
            ❌ Отклонить
          </button>
        </div>
        
        <div v-else-if="selectedOffer.status === 'accepted' && authStore.isStudent" class="space-y-4">
          <a :href="getContactLink(selectedOffer)" target="_blank" 
            class="block w-full py-4 bg-indigo-600 text-center text-white font-bold rounded-2xl hover:bg-indigo-500 transition-all active:scale-95">
            💬 Написать работодателю
          </a>
          <p class="text-center text-xs text-slate-500">Вы приняли это предложение. Свяжитесь с работодателем для обсуждения деталей.</p>
        </div>

        <div v-else-if="selectedOffer.status === 'accepted' && authStore.isEmployer" class="space-y-4">
          <div class="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl text-center">
            <p class="text-emerald-400 font-bold mb-2">🎉 Студент принял ваше предложение!</p>
            <p class="text-sm text-slate-300">Ожидайте сообщения от кандидата по указанным вами контактам.</p>
          </div>
        </div>

        <button @click="selectedOffer = null" 
          class="w-full mt-4 text-slate-500 text-sm font-bold hover:text-white transition-colors py-2">
          Закрыть
        </button>
      </div>
    </div>

    <div v-if="showConfirmModal" class="fixed inset-0 z-[120] flex items-center justify-center p-4 bg-slate-950/90 backdrop-blur-sm" @click.self="showConfirmModal = false">
      <div class="bg-slate-900 border border-indigo-500/30 p-8 rounded-3xl max-w-sm w-full text-center animate-fade-in">
        <div class="w-16 h-16 mx-auto mb-4 rounded-full bg-amber-500/20 flex items-center justify-center">
          <span class="text-3xl">⚠️</span>
        </div>
        <h3 class="text-xl font-bold text-white mb-4">Вы уверены?</h3>
        <p class="text-slate-400 mb-8 text-sm">Это действие нельзя будет отменить.</p>
        <div class="flex gap-3">
          <button @click="handleAction" 
            class="flex-1 py-3 bg-indigo-600 text-white font-bold rounded-xl hover:bg-indigo-500 active:scale-95">
            Да, подтверждаю
          </button>
          <button @click="showConfirmModal = false" 
            class="flex-1 py-3 bg-slate-800 text-slate-300 font-bold rounded-xl hover:bg-slate-700 active:scale-95">
            Отмена
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
.animate-fade-in-up { animation: fade-in-up 0.3s ease-out; }
.animate-fade-in { animation: fade-in 0.2s ease-out; }
</style>