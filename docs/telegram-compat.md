# Telegram compatibility workaround

Python 3.13 requires classes with `__slots__` that support weak references to
explicitly include `"__weakref__"`. Older versions of
[`python-telegram-bot`](https://python-telegram-bot.org/) miss this slot on the
internal `telegram.ext._application.Application` class, causing
`ApplicationBuilder().build()` to fail.

The project temporarily replaces `Application` with a subclass in
`services/api/app/telegram_compat.py`. This subclass extends
`telegram.ext._application.Application` and declares
`__slots__ = (*Base.__slots__, "__weakref__")`, then rebinds
`telegram.ext._application.Application` to itself. Importing the top-level
package (`services.api.app`) applies the patch automatically, so individual
modules or users do not need to import `telegram_compat` manually. This file can
be removed once the `python-telegram-bot` dependency is upgraded to a version
that already includes this fix.
