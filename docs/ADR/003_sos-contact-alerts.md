# ADR 003: SOS Contact Alert Behavior

## Context
Users may need an emergency contact notified when blood sugar repeatedly hits critical levels. The bot already supports saving a contact through `/soscontact` and tracks sugar readings.

## Decision
If a user has set an SOS contact and records three consecutive critical sugar values (below or above their thresholds), the bot sends an alert message containing a placeholder location to both the user and the saved contact.

## Acceptance Scenario
1. **User sets SOS contact**
   - User command: `/soscontact`
   - Bot: `Введите контакт в Telegram (@username) или телефон.`
   - User: `@alice`
   - Bot: `✅ Контакт для SOS сохранён.`
2. **User enters critical sugar three times**
   - Repeated three times:
     - User command: `/sugar`
     - Bot: `Введите текущий уровень сахара (ммоль/л).`
     - User: `3`
     - Bot: `✅ Уровень сахара 3 ммоль/л сохранён.`
3. **Alert dispatch**
   - After the third reading, bot to user: `⚠️ У Ivan критический сахар 3 ммоль/л. 0.0,0.0 https://maps.google.com/?q=0.0,0.0`
   - Bot to `@alice`: `⚠️ У Ivan критический сахар 3 ммоль/л. 0.0,0.0 https://maps.google.com/?q=0.0,0.0`

## Consequences
- Users receive their own alert after the third critical value.
- The SOS contact receives the same alert with a placeholder location until precise geolocation is implemented.

