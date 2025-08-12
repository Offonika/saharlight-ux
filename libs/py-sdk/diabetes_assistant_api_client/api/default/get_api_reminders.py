import logging
from http import HTTPStatus
from typing import Any, Optional, Union

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.reminder import Reminder
from ...types import UNSET, Response, Unset

logger = logging.getLogger(__name__)

def _get_kwargs(
    *,
    telegram_id: int,
    id: Union[Unset, int] = UNSET,
) -> dict[str, Any]:
    params: dict[str, Any] = {}

    params["telegram_id"] = telegram_id

    params["id"] = id

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "get",
        "url": "/api/reminders",
        "params": params,
    }

    return _kwargs


def _parse_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Optional[Union["Reminder", list["Reminder"]]]:
    if response.status_code == 200:

        def _parse_response_200(data: object) -> Union["Reminder", list["Reminder"]]:
            try:
                if not isinstance(data, dict):
                    raise TypeError()
                response_200_type_0 = Reminder.from_dict(data)

                return response_200_type_0
            except (TypeError, ValueError) as exc:
                logger.warning("Failed to parse reminder from dict: %s", exc)
            if not isinstance(data, list):
                raise TypeError()
            response_200_type_1 = []
            _response_200_type_1 = data
            for response_200_type_1_item_data in _response_200_type_1:
                response_200_type_1_item = Reminder.from_dict(response_200_type_1_item_data)

                response_200_type_1.append(response_200_type_1_item)

            return response_200_type_1

        response_200 = _parse_response_200(response.json())

        return response_200
    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: Union[AuthenticatedClient, Client], response: httpx.Response
) -> Response[Union["Reminder", list["Reminder"]]]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    telegram_id: int,
    id: Union[Unset, int] = UNSET,
) -> Response[Union["Reminder", list["Reminder"]]]:
    """List or retrieve reminders

    Args:
        telegram_id (int):
        id (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union['Reminder', list['Reminder']]]
    """

    kwargs = _get_kwargs(
        telegram_id=telegram_id,
        id=id,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: Union[AuthenticatedClient, Client],
    telegram_id: int,
    id: Union[Unset, int] = UNSET,
) -> Optional[Union["Reminder", list["Reminder"]]]:
    """List or retrieve reminders

    Args:
        telegram_id (int):
        id (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union['Reminder', list['Reminder']]
    """

    return sync_detailed(
        client=client,
        telegram_id=telegram_id,
        id=id,
    ).parsed


async def asyncio_detailed(
    *,
    client: Union[AuthenticatedClient, Client],
    telegram_id: int,
    id: Union[Unset, int] = UNSET,
) -> Response[Union["Reminder", list["Reminder"]]]:
    """List or retrieve reminders

    Args:
        telegram_id (int):
        id (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Union['Reminder', list['Reminder']]]
    """

    kwargs = _get_kwargs(
        telegram_id=telegram_id,
        id=id,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: Union[AuthenticatedClient, Client],
    telegram_id: int,
    id: Union[Unset, int] = UNSET,
) -> Optional[Union["Reminder", list["Reminder"]]]:
    """List or retrieve reminders

    Args:
        telegram_id (int):
        id (Union[Unset, int]):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Union['Reminder', list['Reminder']]
    """

    return (
        await asyncio_detailed(
            client=client,
            telegram_id=telegram_id,
            id=id,
        )
    ).parsed
