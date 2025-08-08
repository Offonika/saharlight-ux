export function initProfileForm(): void {
  const form = document.getElementById("profile-form") as HTMLFormElement | null;
  const tg = window.Telegram?.WebApp;
  if (!form) {
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const data: Record<string, string> = {};
    fd.forEach((value, key) => {
      data[key] = String(value);
    });

    const parse = (k: string) => parseFloat(data[k]?.replace(",", "."));
    const icr = parse("icr");
    const cf = parse("cf");
    const target = parse("target");
    const low = parse("low");
    const high = parse("high");

    if ([icr, cf, target, low, high].some((v) => !v || v <= 0) || (low && high && low >= high)) {
      alert("Введите корректные значения профиля");
      return;
    }

    const body = { icr, cf, target, low, high };
    const res = await fetch("/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!res.ok) {
      alert("Не удалось сохранить профиль");
      return;
    }

    tg?.sendData(JSON.stringify(body));
    tg?.close();
  });
}
