Фича: «Мой профиль» (FEATURE / PROFILE / SPEC)

TL;DR: единая точка ввода персональных параметров пользователя. Поддерживает режимы терапии (инсулин/таблетки), валидации, частичный PATCH, отображение контекстной справки в UI и совместимость с ботом.

1. Область и режимы

Сервис обслуживает пациентов на инсулине и без инсулина (СД-2). Для последних — питание/коучинг/напоминания без расчёта болюса (см. Концепция_проекта.md).

Режим терапии: therapyType ∈ {insulin, tablets} (расширяемо).

tablets — болюсные поля скрыты в UI и допускаются NULL на бэке.

insulin — все поля для расчётов доступны.

2. Состав профиля (UI / API / DB)
2.1 Общие поля (всегда)

glucoseUnits — единицы сахара (mmol/L | mg/dL).

target, low, high — целевой уровень и пороги.

timezone, autoTimezone — IANA-таймзона и автодетект (при autoTimezone=true сервер может заменить timezone на device_tz).

quietStart, quietEnd — «тихие часы» (HH:mm).

sosContact, sosEnabled — SOS контакт/флаг (логика см. 003_sos-contact-alerts.md).

2.2 Углеводы

carbUnits ∈ {grams, xe} — формат ввода углеводов.

gramsPerXE — по умолчанию 12, > 0; используется только при carbUnits='xe' (разные школы 10–15 г — оставляем настраиваемым).

2.3 Только для therapyType='insulin'

ICR — углеводный коэффициент (соответствует выбранным carbUnits).

CF — коэффициент чувствительности.

DIA — длительность действия быстрого инсулина, 1–24 ч.

insulinType — тип быстрого.

prebolusMin — предболюс, мин (0–60).

roundingStep — шаг округления дозы, > 0 (напр., 0.1 / 0.5).

maxBolus — ограничение максимального болюса, > 0.

postMealCheckMin — напоминание измерить после еды (0–240).

2.4 Только для therapyType='tablets'

Болюсные поля необязательны/скрыты. (План приёма таблеток — отдельная фича, вне текущего scope.)

Именования:
UI/SDK — camelCase, API — snake_case, БД — snake_case. SDK маппит автоматически.

3. Валидации и предупреждения
3.1 Клиент (UI parseProfile)

Нормализация чисел (,→.), положительность и диапазоны.

Логика: low < target < high, gramsPerXE > 0, roundingStep > 0, DIA ∈ [1;24] (только для insulin), prebolusMin ∈ [0;60], postMealCheckMin ∈ [0;240], maxBolus > 0.

Неблокирующие предупреждения (shouldWarnProfile):

ICR > 8 и CF < 3.

DIA > 12 (мягкое предупреждение).

Смена carbUnits без пересчёта ICR (подсказка к пересчёту).

3.2 Сервер (схемы/сервис)

ProfileSchema (полный GET): подтверждает low < high и low < target < high, валидирует диапазоны.

ProfileSettingsIn/Out (PATCH): валидирует DIA (1–24), rounding_step > 0, carb_units, grams_per_xe > 0, postmeal_check_min ∈ [0;240], timezone.

patch_user_settings:

частичное обновление — сохраняем только переданные поля;

autoTimezone=true ⇒ timezone := device_tz (если передан/доступен);

при therapy_type='tablets' не переопределяем/очищаем болюсные поля (в зависимости от политики, минимум — допускаем NULL).

save_profile/_validate_profile: учитывают режим; в tablets болюсные поля опциональны/игнорируются.

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
  "carb_units": "grams", "grams_per_xe": 12, "rounding_step": 1,
  "postmeal_check_min": 90,
  "timezone": "Europe/Moscow", "auto_timezone": false,
  "quietStart": "23:00", "quietEnd": "07:00",
  "sos_contact": "@user", "sos_enabled": true
}

4.2 Базовое сохранение (исторический)
POST /api/profile/save
Content-Type: application/json


Сохраняет ICR, CF, target, low, high только если therapy_type='insulin' — иначе болюсные игнорируются.

4.3 Частичный апдейт (рекомендуемый)
PATCH /api/profile/settings
Content-Type: application/json


Пример (tablets):

{
  "telegram_id": 448794918,
  "therapy_type": "tablets",
  "timezone": "Europe/Moscow",
  "auto_timezone": false,
  "carb_units": "xe",
  "grams_per_xe": 12,
  "rounding_step": 1,
  "postmeal_check_min": 90
}


Ошибки: 400 — нарушение диапазона/логики; 422 — формат; 404 — профиль отсутствует (если авто-создание отключено).

5. Поведение UI

Динамический рендер полей по therapyType.

Контекстные подсказки («i») у ключевых полей + шторка «Справка».

Локализация RU; числовой ввод — с запятой/точкой.

Состояния: loading / dirty / error / success; disable при отправке.

«Сводка перед сохранением» с предупреждениями.

6. БД и миграции

Параметры распределены между таблицами:

* `users` — данные аккаунта и настройки терапии: `timezone`, `timezone_auto`,
  `dia`, `round_step`, `carb_units`.
* `profiles` — коэффициенты расчётов, пороги сахара, тихие часы и SOS‑параметры.

Дополнительных миграций не требуется: актуальные модели отражают эту схему.

7. SDK и версии

Обновить openapi.json и сгенерировать @saharlight/ts-sdk (workspaces).

Семантика PATCH неизменна; минорный bump SDK.

8. Логи/Аналитика

Логи INFO: краткий диф PATCH (без PII). WARN — подозрительные значения. ERROR — валидации.

События: profile_open, profile_save_success, profile_save_error, therapy_changed.

9. Тестирование и приёмка
9.1 Юнит-тесты (сервер)

Валидации диапазонов, логика low < target < high.

therapy_type='tablets': болюсные поля допускают NULL/игнорируются.

autoTimezone=true ⇒ подмена TZ.

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
UI (camelCase)	API (snake_case)	DB (snake_case)	Диапазон / правило
therapyType	therapy_type	therapy_type	insulin | tablets
glucoseUnits	glucose_units	glucose_units	enum
target	target	target	low < target < high
low	low	low	> 0
high	high	high	> 0
timezone	timezone	timezone	IANA
autoTimezone	auto_timezone	auto_timezone	bool
quietStart	quietStart	quiet_start	HH:mm
quietEnd	quietEnd	quiet_end	HH:mm
sosContact	sos_contact	sos_contact	формат валидируется
sosEnabled	sos_enabled	sos_enabled	bool
carbUnits	carb_units	carb_units	grams | xe
gramsPerXE	grams_per_xe	grams_per_xe	> 0 (по умолчанию 12)
ICR	icr	icr	> 0 (только insulin)
CF	cf	cf	> 0 (только insulin)
DIA	dia_hours	dia_hours	1–24 (только insulin)
insulinType	insulin_type	insulin_type	строка (только insulin)
prebolusMin	prebolus_min	prebolus_min	0–60 (только insulin)
roundingStep	rounding_step	rounding_step	> 0 (только insulin)
maxBolus	max_bolus	max_bolus	> 0 (только insulin)
postMealCheckMin	postmeal_check_min	postmeal_check_min	0–240