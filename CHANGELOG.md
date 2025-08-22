# Changelog

## Unreleased
- Fixed missing role in AuthMiddleware causing 403 on authorized `/api/reminders` requests.
- Changed `/api/reminders`: now returns `200 OK` with an empty list instead of `404` when the user has no active reminders.
