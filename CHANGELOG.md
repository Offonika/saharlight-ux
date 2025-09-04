# Changelog

## Unreleased
- Fixed missing role in AuthMiddleware causing 403 on authorized `/api/reminders` requests.
- Changed `/api/reminders`: returns `200` with an empty list instead of `404` when no reminders exist.
- Changed `/api/stats`: now returns default stats (or `204`) instead of `404` when no data is available.
- Enhanced bot command menu with emojis for easier navigation.
- Updated `ProfileSchema`: field `target` is now optional and aliases `cf`, `targetLow`, `targetHigh` are documented.
- Added learning-mode feature flag and model configuration. See [docs/BRD.md](docs/BRD.md) and [docs/Концепция_проекта.md](docs/Концепция_проекта.md).
