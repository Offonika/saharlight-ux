# Changelog

## Unreleased

### Added
- `insulin_short`, `insulin_long` (split insulin doses). Подробнее см. [DoD Master](docs/feature-dod/split-insulin-doses.md) и [ADR 005](docs/ADR/005-split-insulin-doses.md).

### Deprecated
- `dose` — легаси-поле для доз инсулина. Мы завершим поддержку в релизе **v3.0** (ориентировочно 2026‑03‑01); до удаления значение
  будет автоматически копироваться в `insulin_short`. Клиентам рекомендовано перейти на явные поля `insulin_short` и `insulin_long` заранее.
