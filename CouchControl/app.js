(() => {
  const tg = window.Telegram?.WebApp;
  if (tg) { tg.ready(); tg.expand(); }
  const tabs = [...document.querySelectorAll(".tab")];
  const titles = {touchpad:"Тачпад",keyboard:"Клавиатура",buttons:"Кнопки"};
  const counts = {touchpad:"01 / 03",keyboard:"02 / 03",buttons:"03 / 03"};
  const hints = {
    touchpad:"Проведи пальцем по области, чтобы двигать курсор на ПК.",
    keyboard:"Клавиши подключим следующим этапом.",
    buttons:"Кнопки управления подключим следующим этапом."
  };
  tabs.forEach(tab => tab.addEventListener("click", () => {
    const mode = tab.dataset.mode;
    tabs.forEach(item => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".mode-view").forEach(view => view.classList.toggle("active", view.id === mode + "-view"));
    document.getElementById("mode-title").textContent = titles[mode];
    document.querySelector(".mode-count").textContent = counts[mode];
    document.getElementById("demo-hint").textContent = hints[mode];
  }));

  const input = document.getElementById("api-url");
  const status = document.getElementById("connection-status");
  const connect = document.getElementById("connect-btn");
  const touchpad = document.getElementById("touchpad");
  let apiBase = localStorage.getItem("couchcontrol_api") || new URLSearchParams(location.search).get("api") || "";
  if (apiBase) input.value = apiBase;

  const request = async (path, payload) => {
    if (!apiBase || !tg?.initData) throw new Error("Открой Mini App из Telegram и укажи адрес соединения.");
    const response = await fetch(apiBase + path, {
      method: "POST",
      headers: {"Content-Type":"application/json","X-Telegram-Init-Data":tg.initData},
      body: JSON.stringify(payload)
    });
    if (!response.ok) throw new Error("Ошибка соединения (" + response.status + ")");
    return response.json();
  };

  connect.addEventListener("click", async () => {
    const value = input.value.trim().replace(/\/$/, "");
    if (!/^https:\/\/[a-z0-9.-]+$/.test(value)) {
      status.textContent = "Введи HTTPS-адрес Cloudflare Tunnel.";
      return;
    }
    try {
      const response = await fetch(value + "/api/health");
      if (!response.ok) throw new Error("Сервер не ответил");
      apiBase = value;
      localStorage.setItem("couchcontrol_api", apiBase);
      status.textContent = "Сервер найден. Проверяем Telegram-доступ при первом движении.";
    } catch (_error) {
      status.textContent = "Не удалось связаться с ПК. Проверь адрес и запущенный туннель.";
    }
  });

  let active = false;
  let lastX = 0, lastY = 0, lastSent = 0;
  let pendingX = 0, pendingY = 0;
  let sending = false;
  const flushMove = async () => {
    if (sending || (!pendingX && !pendingY)) return;
    const dx = pendingX, dy = pendingY;
    pendingX = 0; pendingY = 0; sending = true;
    try { await request("/api/mouse/move", {dx, dy}); }
    catch (error) { status.textContent = error.message; }
    finally { sending = false; }
  };

  touchpad.addEventListener("pointerdown", event => {
    active = true; lastX = event.clientX; lastY = event.clientY;
    touchpad.setPointerCapture(event.pointerId);
    if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
  });
  touchpad.addEventListener("pointermove", event => {
    if (!active) return;
    const dx = (event.clientX - lastX) * 1.7;
    const dy = (event.clientY - lastY) * 1.7;
    lastX = event.clientX; lastY = event.clientY;
    pendingX += dx; pendingY += dy;
    const now = performance.now();
    if (now - lastSent > 32) { lastSent = now; flushMove(); }
  });
  const endPointer = () => { active = false; flushMove(); };
  touchpad.addEventListener("pointerup", endPointer);
  touchpad.addEventListener("pointercancel", endPointer);

  document.querySelectorAll(".mouse-btn").forEach(button => {
    button.addEventListener("click", async () => {
      try { await request("/api/mouse/click", {button:button.dataset.button}); }
      catch (error) { status.textContent = error.message; }
    });
  });
  document.querySelectorAll(".key,.action-tile").forEach(button => {
    button.addEventListener("click", () => {
      if (tg?.HapticFeedback) tg.HapticFeedback.selectionChanged();
      document.getElementById("demo-hint").textContent = "Эта функция будет подключена следующим этапом.";
    });
  });
})();