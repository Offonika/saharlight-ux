# Changelog

## Unreleased
- Fixed missing role in AuthMiddleware causing 403 on authorized `/api/reminders` requests.
- Changed `/api/reminders`: returns `200` with an empty list instead of `404` when no reminders exist.
- Changed `/api/stats`: now returns default stats (or `204`) instead of `404` when no data is available.
