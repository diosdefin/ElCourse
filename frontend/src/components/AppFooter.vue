<template>
  <footer class="relative border-t border-slate-800/60 bg-gradient-to-b from-slate-950/90 to-slate-950/40 backdrop-blur-sm">
    <!-- Декоративный элемент сверху -->
    <div class="absolute -top-px left-0 right-0 h-px bg-gradient-to-r from-transparent via-indigo-500/50 to-transparent"></div>

    <div class="mx-auto w-full max-w-[1180px] px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
      <div class="grid gap-8 md:grid-cols-3 lg:gap-12">
        
        <!-- Колонка 1: Лого + описание -->
        <div class="space-y-4">
          <RouterLink to="/" class="group inline-flex items-center gap-2.5">
            <span class="relative flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-600 text-xs font-black tracking-wide text-white shadow-lg shadow-indigo-500/30 transition-all duration-300 group-hover:scale-105 group-hover:shadow-indigo-500/50">
              EL
              <!-- анимированный градиент при ховере -->
              <span class="absolute inset-0 rounded-xl bg-gradient-to-br from-indigo-400 to-indigo-600 opacity-0 blur-md transition-opacity group-hover:opacity-100"></span>
            </span>
            <span class="text-base font-black tracking-[0.14em] text-white transition group-hover:text-indigo-300 sm:text-[1rem] sm:tracking-[0.16em]">COURSE</span>
          </RouterLink>
          <p class="max-w-md text-xs leading-5 text-slate-400 sm:text-[13px] sm:leading-[1.4rem]">
            Образовательная платформа для курсов, тестов, подтверждённых навыков и карьерного взаимодействия.
          </p>
        </div>

        <!-- Колонка 2: Навигация (вертикальные ссылки) -->
        <nav class="grid grid-cols-3 gap-3 text-sm sm:grid-cols-2 md:flex md:flex-col" aria-label="Навигация">
          <p class="col-span-3 text-[11px] font-black uppercase tracking-[0.2em] text-slate-500 sm:col-span-2">Навигация</p>
          <RouterLink class="text-slate-300 transition hover:text-white hover:translate-x-0.5 inline-block w-fit" to="/">Главная</RouterLink>
          <RouterLink class="text-slate-300 transition hover:text-white hover:translate-x-0.5 inline-block w-fit" to="/courses">Курсы</RouterLink>
          <RouterLink class="text-slate-300 transition hover:text-white hover:translate-x-0.5 inline-block w-fit" to="/vacancies">Вакансии</RouterLink>
          </nav>

        <!-- Колонка 3: Платформа + Контакты в виде кликабельных ссылок -->
        <div class="grid gap-6 sm:grid-cols-2 md:flex md:flex-col">
          
          <div class="space-y-2.5">
            <p class="text-[11px] font-black uppercase tracking-[0.2em] text-slate-500">Контакты</p>
            <p class="text-xs leading-5 text-slate-400 sm:text-[13px]">
              <a href="mailto:support@elcourse.com" class="transition hover:text-indigo-400">support@elcourse.com</a><br>
              <span class="text-slate-500">+996 (221) 14-08-07</span>
            </p>
          </div>
        </div>
      </div>

      <!-- Нижняя полоса с копирайтом и языком -->
      <div class="mt-8 flex flex-col justify-center gap-3 border-t border-slate-800/50 pt-5 text-center text-[11px] text-slate-500 sm:flex-row sm:items-center sm:pt-6 sm:text-left">
        <p>© 2026 ElCourse. Образовательная платформа.</p>
      </div>
    </div>
  </footer>
</template>