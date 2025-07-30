from telegram.ext import (
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)

from .handlers import (
    cancel_handler,
    freeform_handler,
    sugar_start,
    sugar_val,
    photo_handler,
    doc_handler,
    photo_sugar_handler,
    dose_start,
    dose_method_choice,
    dose_xe_handler,
    dose_sugar,
    dose_carbs,
    profile_start,
    profile_icr,
    profile_cf,
    profile_target,
    onb_hello,
    onb_begin,
    onb_icr,
    onb_cf,
    onb_target,
    onb_demo_run,
)

from .handlers import (
    PROFILE_ICR,
    PROFILE_CF,
    PROFILE_TARGET,
    DOSE_METHOD,
    DOSE_XE,
    DOSE_SUGAR,
    DOSE_CARBS,
    PHOTO_SUGAR,
    SUGAR_VAL,
    ONB_HELLO,
    ONB_PROFILE_ICR,
    ONB_PROFILE_CF,
    ONB_PROFILE_TARGET,
    ONB_DEMO,
)

# Onboarding conversation
onboarding_conv = ConversationHandler(
    entry_points=[CommandHandler("start", onb_hello)],
    states={
        ONB_HELLO: [CallbackQueryHandler(onb_begin, pattern="^onb:start$")],
        ONB_PROFILE_ICR: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_icr)],
        ONB_PROFILE_CF: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_cf)],
        ONB_PROFILE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, onb_target)],
        ONB_DEMO: [CallbackQueryHandler(onb_demo_run, pattern="^onb:demo$")],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler),
    ],
)

# Sugar conversation
sugar_conv = ConversationHandler(
    entry_points=[CommandHandler("sugar", sugar_start)],
    states={
        SUGAR_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, sugar_val)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler),
    ],
)

# Photo processing conversation
photo_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.PHOTO, photo_handler),
        MessageHandler(filters.Document.IMAGE, doc_handler),
    ],
    states={
        PHOTO_SUGAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, photo_sugar_handler)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler),
    ],
)

# Dose calculation conversation
dose_conv = ConversationHandler(
    entry_points=[
        CommandHandler("dose", dose_start),
        MessageHandler(filters.Regex("^💉 Доза инсулина$"), dose_start),
    ],
    states={
        DOSE_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_method_choice)],
        DOSE_XE: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_xe_handler)],
        DOSE_SUGAR: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_sugar)],
        DOSE_CARBS: [MessageHandler(filters.TEXT & ~filters.COMMAND, dose_carbs)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler),
    ],
)

# Profile editing conversation
profile_conv = ConversationHandler(
    entry_points=[
        CommandHandler("profile", profile_start),
        MessageHandler(filters.Regex(r"^🔄 Изменить профиль$"), profile_start),
    ],
    states={
        PROFILE_ICR: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_icr)],
        PROFILE_CF: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_cf)],
        PROFILE_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_target)],
    },
    fallbacks=[
        CommandHandler("cancel", cancel_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, freeform_handler),
    ],
)
