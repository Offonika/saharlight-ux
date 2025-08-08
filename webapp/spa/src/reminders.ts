export function initReminders(): void {
  const listEl = document.getElementById("reminders-list");
  const form = document.getElementById("reminder-form") as HTMLFormElement | null;
  const tg = window.Telegram?.WebApp;

  async function load() {
    const res = await fetch("/reminders");
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && listEl) {
        listEl.innerHTML = "";
        for (const item of data) {
          const li = document.createElement("li");
          li.textContent = item.text ?? "";
          listEl.appendChild(li);
        }
      }
    }
  }

  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const data: Record<string, string> = {};
    fd.forEach((value, key) => {
      data[key] = String(value);
    });
    const res = await fetch("/reminders", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      alert("Не удалось сохранить напоминание");
      return;
    }
    tg?.sendData(JSON.stringify(data));
    form.reset();
    await load();
  });

  load();
}
