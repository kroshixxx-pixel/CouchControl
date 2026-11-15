(() => {
  const tg = window.Telegram?.WebApp;
  if (tg) { tg.ready(); tg.expand(); }
  const tabs = [...document.querySelectorAll(".tab")];
  const titles = {touchpad:"Тачпад",keyboard:"Клавиатура",buttons:"Кнопки"};
  const counts = {touchpad:"01 / 03",keyboard:"02 / 03",buttons:"03 / 03"};
  const hints = {
    touchpad:"Интерфейс готов. Движение курсора пока не отправляется на ПК.",
    keyboard:"Клавиши показаны как макет. Передача ввода появится после подключения ПК.",
    buttons:"Кнопки пока демонстрационные. Команды будут включены после подключения ПК."
  };
  tabs.forEach(tab => tab.addEventListener("click", () => {
    const mode = tab.dataset.mode;
    tabs.forEach(item => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".mode-view").forEach(view => view.classList.toggle("active", view.id === mode + "-view"));
    document.getElementById("mode-title").textContent = titles[mode];
    document.querySelector(".mode-count").textContent = counts[mode];
    document.getElementById("demo-hint").textContent = hints[mode];
  }));
  document.querySelectorAll(".mouse-btn,.key,.action-tile").forEach(button => {
    button.addEventListener("click", () => {
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
      document.getElementById("demo-hint").textContent = "Демо-режим: действие пока не отправлено на компьютер.";
    });
  });
})();