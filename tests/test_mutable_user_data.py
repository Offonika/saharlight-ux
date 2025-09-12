from types import MappingProxyType, SimpleNamespace

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


def test_get_mutable_user_data_from_mapping_proxy() -> None:
    proxy = MappingProxyType(
        {
            photo_handlers.WAITING_GPT_FLAG: True,
            photo_handlers.WAITING_GPT_TIMESTAMP: 1,
        }
    )
    context = SimpleNamespace(user_data=proxy)
    user_data = photo_handlers._get_mutable_user_data(context)
    assert not isinstance(user_data, MappingProxyType)
    user_data["pending_entry"] = {"value": 1}
    photo_handlers._clear_waiting_gpt(context)
    assert photo_handlers.WAITING_GPT_FLAG not in context._user_data
    assert photo_handlers.WAITING_GPT_TIMESTAMP not in context._user_data
    assert context._user_data["pending_entry"] == {"value": 1}
    assert photo_handlers._get_mutable_user_data(context) is user_data
    assert context.user_data is proxy
