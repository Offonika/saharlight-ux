import { initProfileForm } from "./profile";
import { initReminders } from "./reminders";

const tg = window.Telegram?.WebApp;

if (tg) {
  tg.ready();
}

const path = window.location.pathname.replace(/^\/ui/, "");

if (path.startsWith("/profile")) {
  initProfileForm();
} else if (path.startsWith("/reminders")) {
  initReminders();
} else {
  const tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  tg?.sendData(tz);
  tg?.close();
}
