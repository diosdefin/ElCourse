<template>
  <footer class="border-t border-slate-800 bg-slate-950/70">
    <div class="mx-auto w-full max-w-7xl px-4 py-5 text-sm text-slate-400 sm:px-6 sm:py-6 lg:px-8">
      <div class="grid gap-5 md:grid-cols-[1.2fr_0.8fr_0.9fr] md:gap-8">
        <div class="min-w-0">
          <RouterLink to="/" class="inline-flex items-center gap-3 text-white">
            <span class="flex h-8 w-8 items-center justify-center rounded-xl bg-indigo-500 text-[11px] font-black tracking-wide shadow-lg shadow-indigo-500/20 sm:h-9 sm:w-9 sm:text-xs">
              EL
            </span>
            <span class="text-base font-black tracking-[0.16em] sm:text-lg sm:tracking-[0.18em]">COURSE</span>
          </RouterLink>
          <p class="mt-2 max-w-md text-xs leading-5 text-slate-400 sm:mt-4 sm:text-sm sm:leading-6">
            Образовательная платформа для курсов, тестов, подтверждённых навыков и карьерного взаимодействия.
          </p>
        </div>

        <nav class="grid grid-cols-3 gap-2 text-xs sm:gap-3 sm:text-sm md:grid-cols-1" aria-label="Навигация">
          <p class="col-span-3 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 md:col-span-1">Навигация</p>
          <RouterLink class="font-semibold transition hover:text-white" to="/">Главная</RouterLink>
          <RouterLink class="font-semibold transition hover:text-white" to="/courses">Курсы</RouterLink>
          <RouterLink class="font-semibold transition hover:text-white" to="/vacancies">Вакансии</RouterLink>
        </nav>

        <div class="hidden gap-5 sm:grid sm:grid-cols-2 md:grid-cols-1">
          <div class="grid gap-3">
            <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Платформа</p>
            <span>Для студентов</span>
            <span>Для преподавателей</span>
            <span>Для работодателей</span>
          </div>

          <div>
            <p class="text-xs font-black uppercase tracking-[0.2em] text-slate-500">Контакты</p>
            <p class="mt-3 leading-6">Контактная информация указывается администратором платформы.</p>
          </div>
        </div>
      </div>
    </div>

    <div class="border-t border-slate-800/80 px-4 py-3 text-center text-[11px] text-slate-500 sm:py-4 sm:text-xs">
      © 2026 ElCourse. Образовательная платформа.
    </div>
  </footer>
</template>
