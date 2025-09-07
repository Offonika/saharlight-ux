Фича: «Мой профиль» (FEATURE / PROFILE / SPEC)

TL;DR: единая точка ввода персональных параметров пользователя. Поддерживает режимы терапии (инсулин/таблетки), валидации, частичный PATCH, отображение контекстной справки в UI и совместимость с ботом.

1. Область и режимы

Сервис обслуживает пациентов на инсулине, таблетках, смешанной терапии и без медикаментозного лечения (СД‑2). Для последних — питание/коучинг/напоминания без расчёта болюса (см. Концепция_проекта.md).

Режим терапии: therapyType ∈ {insulin, tablets, none, mixed}.

insulin — все поля для расчётов доступны.

tablets — болюсные поля скрыты в UI и допускаются NULL на бэке.

none — медикаментозная терапия отсутствует; UI скрывает болюсные поля, сервер игнорирует связанные значения.

mixed — инсулин + таблетки; UI ведёт себя как для insulin, план таблеток вне текущего scope.

2. Состав профиля (UI / API / DB)
2.1 Общие поля (всегда)

glucoseUnits — единицы сахара (mmol/L | mg/dL).

target, low, high — целевой уровень и пороги.

timezone, timezoneAuto — IANA-таймзона и автодетект (при timezoneAuto=true сервер может заменить timezone на device_tz).

quietStart, quietEnd — «тихие часы» (HH:mm).

sosContact, sosAlertsEnabled — SOS контакт и флаг включения оповещений (логика см. 003_sos-contact-alerts.md).

2.2 Углеводы

carbUnits ∈ {grams, xe} — формат ввода углеводов.

gramsPerXE — по умолчанию 12, > 0; используется только при carbUnits='xe' (разные школы 10–15 г — оставляем настраиваемым).

2.3 Только для therapyType='insulin' или 'mixed'

ICR — углеводный коэффициент (соответствует выбранным carbUnits).

CF — коэффициент чувствительности.

DIA — длительность действия быстрого инсулина, 1–24 ч.;
влияет на учёт IOB при расчёте болюса.

insulinType — тип быстрого *(не запланировано)*.

preBolus — предболюс, мин (0–60).

roundStep — шаг округления дозы, > 0 (напр., 0.1 / 0.5).

maxBolus — ограничение максимального болюса, > 0.

postMealCheckMin — напоминание измерить после еды (0–240).

2.4 Только для therapyType='tablets' или 'none'

Болюсные поля необязательны/скрыты. (План приёма таблеток — отдельная фича, вне текущего scope.)

Именования:
UI/SDK — camelCase, API — snake_case, БД — snake_case. SDK маппит автоматически.

3. Валидации и предупреждения
3.1 Клиент (UI parseProfile)

Нормализация чисел (,→.), положительность и диапазоны.

Логика: low < target < high, gramsPerXE > 0, roundStep > 0, DIA ∈ [1;24] (только для insulin/mixed), preBolus ∈ [0;60], postMealCheckMin ∈ [0;240], maxBolus > 0.

Неблокирующие предупреждения (shouldWarnProfile):

ICR > 8 и CF < 3.

DIA > 12 (мягкое предупреждение).

Смена carbUnits без пересчёта ICR (подсказка к пересчёту).

3.2 Сервер (схемы/сервис)

ProfileSchema (полный GET): подтверждает low < high и low < target < high, валидирует диапазоны.

ProfileSettingsIn/Out (PATCH): валидирует DIA (1–24), round_step > 0, carb_units, grams_per_xe > 0, postmeal_check_min ∈ [0;240], timezone.

patch_user_settings:

частичное обновление — сохраняем только переданные поля;

timezoneAuto=true ⇒ timezone := device_tz (если передан/доступен);

при therapy_type='tablets' или 'none' не переопределяем/очищаем болюсные поля (в зависимости от политики, минимум — допускаем NULL).

save_profile/_validate_profile: учитывают режим; в tablets/none болюсные поля опциональны/игнорируются.

4. API контракты
4.1 Получение
GET /api/profile?telegramId={number}
Accept: application/json


200 OK (пример):

{
  "telegram_id": 448794918,
  "therapy_type": "tablets",
  "glucose_units": "mmol/L",
  "target": 5.5, "low": 3.9, "high": 8.0,

  "carb_units": "g", "grams_per_xe": 12, "round_step": 1,
  "postmeal_check_min": 90,
  "timezone": "Europe/Moscow", "timezone_auto": false,
  "quiet_start": "23:00", "quiet_end": "07:00",

  "sos_contact": "@user", "sos_alerts_enabled": true
}

4.2 Базовое сохранение
POST /api/profile
Content-Type: application/json


Сохраняет ICR, CF, target, low, high только если therapy_type='insulin' или 'mixed' — иначе болюсные игнорируются.

4.3 Частичный апдейт (рекомендуемый)
PATCH /api/profile
Content-Type: application/json


Пример (tablets; аналогично none):

{
  "telegram_id": 448794918,
  "therapy_type": "tablets",
  "timezone": "Europe/Moscow",
  "timezone_auto": false,
  "carb_units": "xe",
  "grams_per_xe": 12,
  "round_step": 1,
  "postmeal_check_min": 90
}


Ошибки: 400 — нарушение диапазона/логики; 422 — формат; 404 — профиль отсутствует (если авто-создание отключено).

5. Поведение UI

Динамический рендер полей по therapyType: insulin/mixed — показывают болюсные поля, tablets/none — скрывают.

Контекстные подсказки («i») у ключевых полей + шторка «Справка».

Локализация RU; числовой ввод — с запятой/точкой.

Состояния: loading / dirty / error / success; disable при отправке.

«Сводка перед сохранением» с предупреждениями.

6. БД и миграции

Таблица profiles (уже есть): добавить поля
timezone TEXT NOT NULL DEFAULT 'UTC',
timezone_auto BOOLEAN NOT NULL DEFAULT TRUE,
dia NUMERIC NOT NULL DEFAULT 4.0,
round_step NUMERIC NOT NULL DEFAULT 0.5,
carb_units TEXT CHECK ('g','xe') DEFAULT 'g' NOT NULL,
grams_per_xe NUMERIC DEFAULT 12 CHECK (grams_per_xe > 0),
therapy_type TEXT CHECK ('insulin','tablets','none','mixed') DEFAULT 'insulin' NOT NULL,
glucose_units TEXT DEFAULT 'mmol/L' NOT NULL,
prebolus_min SMALLINT DEFAULT 0 CHECK (prebolus_min BETWEEN 0 AND 60),
max_bolus NUMERIC DEFAULT 10 CHECK (max_bolus > 0),
postmeal_check_min SMALLINT DEFAULT 0 CHECK (postmeal_check_min BETWEEN 0 AND 240).

// поле insulin_type пока не планируется

Политика NULL для болюсных полей при therapy_type='tablets' или 'none' — через бизнес-валидацию (предпочтительно), без жёстких CHECK.

Backfill: существующим проставить therapy_type='insulin'.

7. SDK и версии

Обновить openapi.json и сгенерировать @saharlight/ts-sdk (workspaces).

Семантика PATCH неизменна; минорный bump SDK.

8. Логи/Аналитика

Логи INFO: краткий диф PATCH (без PII). WARN — подозрительные значения. ERROR — валидации.

События: profile_open, profile_save_success, profile_save_error, therapy_changed.

9. Тестирование и приёмка
9.1 Юнит-тесты (сервер)

Валидации диапазонов, логика low < target < high.

therapy_type='tablets' или 'none': болюсные поля допускают NULL/игнорируются.

timezoneAuto=true ⇒ подмена TZ.

9.2 Юнит-тесты (UI)

parseProfile: нормализация чисел, диапазоны, ветки therapyType.

shouldWarnProfile: ICR>8 && CF<3, DIA>12, смена carbUnits.

9.3 Интеграционные

PATCH→GET в обоих режимах; смена режимов туда-обратно без потери данных вне режима.

Регрессия исторического POST /profile/save.

9.4 DoD (Definition of Done)

✅ UI динамически скрывает/показывает поля по therapyType.

✅ Сервер корректно валидирует и частично обновляет поля.

✅ OpenAPI/SDK обновлены, фронт собирается.

✅ Тесты зелёные, ручные сценарии из 9.3 проходят.

10. Вне рамок (не входит)

Планировщик приёма таблеток и связанные напоминания (отдельная фича).

Импорт/экспорт профиля.

11. Матрица соответствия полей
UI (camelCase)  API (snake_case)        DB (snake_case) Диапазон / правило
therapyType     therapy_type    therapy_type    insulin | tablets | none | mixed
glucoseUnits    glucose_units   glucose_units   enum
target  target  target  low < target < high
low     low     low     > 0
high    high    high    > 0
timezone        timezone        timezone        IANA
timezoneAuto    timezone_auto   timezone_auto   bool
quietStart      quiet_start      quiet_start     HH:mm
quietEnd        quiet_end        quiet_end       HH:mm
sosContact      sos_contact     sos_contact     формат валидируется
sosAlertsEnabled      sos_alerts_enabled     sos_alerts_enabled     bool, включает отправку SOS-оповещений
carbUnits       carb_units      carb_units      g | xe
gramsPerXE      grams_per_xe    grams_per_xe    > 0 (по умолчанию 12)
ICR     icr     icr     > 0 (только insulin/mixed)
CF      cf      cf      > 0 (только insulin/mixed)
DIA     dia            dia            1–24 (только insulin/mixed), учитывается в IOB

insulinType     insulin_type    insulin_type    строка (только insulin/mixed) *(не запланировано)*
prebolusMin     prebolus_min    prebolus_min    0–60 (только insulin/mixed)
roundingStep    round_step      round_step      > 0 (только insulin/mixed)

maxBolus        max_bolus       max_bolus       > 0 (только insulin/mixed)
postMealCheckMin        postmeal_check_min      postmeal_check_min      0–240
