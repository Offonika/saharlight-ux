class ApplicationBuilder:
    def __init__(self, *a, **k):
        pass

class CommandHandler:
    def __init__(self, *a, **k):
        pass

class MessageHandler:
    def __init__(self, *a, **k):
        pass

class CallbackQueryHandler:
    def __init__(self, *a, **k):
        pass

class ConversationHandler:
    END = object()
    def __init__(self, *a, **k):
        pass

class ContextTypes:
    DEFAULT_TYPE = object

class filters:
    PHOTO = object()
    TEXT = object()
    COMMAND = object()
    Document = type('Document', (), {'IMAGE': object()})
    Regex = lambda x: x

