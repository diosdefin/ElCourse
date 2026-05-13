<script setup>
const currentYear = new Date().getFullYear()
</script>

<template>
  <footer class="border-t border-slate-800 bg-slate-950/70">
    <div class="mx-auto grid w-full max-w-7xl gap-8 px-4 py-8 text-sm text-slate-400 sm:px-6 md:grid-cols-[1.2fr_0.8fr_0.9fr] lg:px-8">
      <div class="min-w-0">
        <RouterLink to="/" class="inline-flex items-center gap-3 text-white">
          <span class="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500 text-xs font-black tracking-wide shadow-lg shadow-indigo-500/20">
            EL
          </span>
          <span class="text-lg font-black tracking-[0.18em]">COURSE</span>
        </RouterLink>
        <p class="mt-4 max-w-md leading-6">
          Платформа для онлайн-курсов, проверки знаний, профиля навыков и карьерных возможностей.
        </p>
      </div>

      <nav class="grid gap-3" aria-label="Публичные страницы">
        <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Разделы</p>
        <RouterLink class="w-fit font-semibold transition hover:text-white" to="/">Главная</RouterLink>
        <RouterLink class="w-fit font-semibold transition hover:text-white" to="/courses">Курсы</RouterLink>
        <RouterLink class="w-fit font-semibold transition hover:text-white" to="/vacancies">Вакансии</RouterLink>
      </nav>

      <div class="grid gap-5 sm:grid-cols-2 md:grid-cols-1">
        <div class="grid gap-3">
          <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Платформа</p>
          <span>Для студентов</span>
          <span>Для преподавателей</span>
          <span>Для работодателей</span>
        </div>

        <div>
          <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Контакты</p>
          <p class="mt-3 leading-6">Контактная информация указывается администратором.</p>
        </div>
      </div>
    </div>

    <div class="border-t border-slate-800/80 px-4 py-4 text-center text-xs text-slate-500">
      © {{ currentYear }} ElCourse. Все права защищены.
    </div>
  </footer>
</template>
