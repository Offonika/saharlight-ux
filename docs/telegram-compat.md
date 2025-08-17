# Telegram compatibility workaround

Python 3.13 requires classes with `__slots__` that support weak references to
explicitly include `"__weakref__"`. Older versions of
[`python-telegram-bot`](https://python-telegram-bot.org/) miss this slot on the
internal `telegram.ext._application.Application` class, causing
`ApplicationBuilder().build()` to fail.

The project temporarily patches `Application.__slots__` in
`services/api/app/telegram_compat.py`. This file can be removed once the
`python-telegram-bot` dependency is upgraded to a version that already includes
this fix.
