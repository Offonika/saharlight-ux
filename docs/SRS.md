 Software Requirements Specification (SRS)
**СахарФото v 2.0** · август 2025

---
## 1 · Область применения
Телеграм‑бот, сервер ИИ и SaaS‑панель врача для поддержки людей с диабетом (приоритет — СД‑2).

---
## 2 · Функциональные требования

### 2.1 Telegram‑бот
| ID | Требование | Приёмочный критерий |
|----|------------|---------------------|
| F‑BOT‑01 | `/start` запускает wizard‑онбординг (3 шага) и меню | ≥ 70 % пользователей завершают онбординг |
| F‑BOT‑02 | Команды: `/photo`, `/xe`, `/sugar`, `/dose`, `/history`, `/profile`, `/trial`, `/help`, `/reset` | Каждая команда отвечает < 2 с |
| F‑BOT‑03 | Фото еды → `cv_service` → `{class,mass_g,carbs_g,xe}` → запись в БД | MAE ХЕ ≤ 15 % |
| F‑BOT‑04 | Голосовой ввод (Whisper ≤ 30 с) | WER ≤ 5 % |
| F‑BOT‑05 | Напоминания: сахар, длинный инсулин, таблетки | Джоб триггерится 100 % |
| F‑BOT‑06 | SOS‑alert при 3 критических BG подряд | Уходит 2 сообщения (user + SOS) |
| F‑BOT‑07 | 14‑д Pro‑trial `/trial` + paywall `/upgrade` | Конверсия trial→pay ≥ 30 % |

### 2.2 Сервер
| ID | Требование | Приёмочный критерий |
|----|------------|---------------------|
| F‑SRV‑01 | REST+gRPC (FastAPI) `/predict`, `/entries`, `/alerts`, `/reports` | P95 \< 300 мс |
| F‑SRV‑02 | CV‑сервис: YOLOv8‑seg → TensorRT | mAP50 ≥ 0.70 |
| F‑SRV‑03 | Алгоритм болюса (ICR/CF + IOB) | MAE болюса ≤ 1,2 ед. |
| F‑SRV‑04 | LibreLinkUp pull 5 мин + Redis‑кэш | 95 % успешных fetch/сутки |
| F‑SRV‑05 | Celery‑алерты + Redis | Алерт < 10 с |

### 2.3 SaaS‑панель
| ID | Требование | Приёмочный критерий |
|----|------------|---------------------|
| F‑WEB‑01 | OAuth 2.1, список пациентов | TTFB < 500 мс |
| F‑WEB‑02 | Лента BG/ХЕ/доз/аларм | Real‑time WS обновление |
| F‑WEB‑03 | PDF‑отчёт 7/14/30 д | Генерация ≤ 30 с |
| F‑WEB‑04 | FHIR/HL7‑export | FHIR validator = 0 ошибок |

---
## 3 · Нефункциональные требования
| Категория | Значение |
|-----------|----------|
| Производительность | 1 000 req/min; P95 Bot→Backend < 400 мс |
| Доступность | ≥ 99,5 % в квартал |
| Масштабируемость | Горизонтальный Celery & cv_service |
| Безопасность | TLS 1.3, AES‑256 at‑rest, OAuth PKCE, 2FA admin |
| Регуляторика | 152‑ФЗ, SaMD I, фото ≤ 45 дн, CGM ≤ 30 дн |
| Локализация | RU, en‑US через i18n |

---
## 4 · Технологический стек
* **Backend:** Python 3.10 · FastAPI · SQLAlchemy · Celery/Redis  
* **CV:** PyTorch 2, YOLOv8‑seg → TensorRT → SnakeDNN (релиз)  
* **LLM:** OpenAI GPT‑4o (fallback Llama‑3‑Ru)  
* **DB:** PostgreSQL 15, Redis 7  
* **DevOps:** Docker Compose → K8s, GitHub Actions, Trivy  
* **Хостинг:** Tier III RU, 2 × A100 40 GB, MinIO, MLflow

---
## 5 · Интерфейсы
| Interface | Протокол | Формат | Auth |
|-----------|----------|--------|------|
| Bot ↔ Backend | HTTPS REST | JSON | Bot token |
| Backend ↔ cv_service | gRPC | Proto3 | mTLS |
| Backend ↔ LibreLinkUp | HTTPS REST | JSON | OAuth2 |
| Backend ↔ Web | HTTPS REST/WS | JSON | JWT |

---
## 6 · Качество кода и CI/CD
* `black` + `ruff` + `mypy --strict` — 0 warning  
* Coverage ≥ 85 % (pytest), e2e — Playwright  
* Docker‑image < 700 MB; build+push ≤ 10 мин  
* CI pipeline: test → build → scan → deploy

---
## 7 · Открытые вопросы
1. Геолокация в SOS‑alert (Live Location vs SDK).  
2. SnakeDNN или Inferentia как финальный inference.  
3. Storage CGM‑raw — TimescaleDB partition?