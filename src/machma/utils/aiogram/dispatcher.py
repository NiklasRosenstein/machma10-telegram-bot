
from aiogram import Bot, Dispatcher


class ProxyDispatcher:

    def __init__(self):
        self._message_handlers = []

    def message_handler(self, *args, **kwargs):
        def decorator(func):
            self._message_handlers.append((func, args, kwargs))
            return func
        return decorator

    def to_dispatcher(self, bot: Bot) -> Dispatcher:
        dp = Dispatcher(bot)
        for func, args, kwargs in self._message_handlers:
            dp.message_handler(*args, **kwargs)(func)
        return dp
