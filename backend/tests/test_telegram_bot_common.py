from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.exceptions import TelegramBadRequest

from vpn_core.telegram_bot.handlers.common import edit_callback_message


@pytest.mark.asyncio
async def test_edit_callback_message_uses_edit_text_for_plain_messages():
    message = MagicMock()
    message.photo = None
    message.document = None
    message.video = None
    message.animation = None
    message.edit_text = AsyncMock()
    message.edit_caption = AsyncMock()

    await edit_callback_message(message, "hello")

    message.edit_text.assert_awaited_once()
    message.edit_caption.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_callback_message_uses_edit_caption_for_photos():
    message = MagicMock()
    message.photo = [MagicMock()]
    message.document = None
    message.video = None
    message.animation = None
    message.edit_text = AsyncMock()
    message.edit_caption = AsyncMock()

    await edit_callback_message(message, "receipt approved")

    message.edit_caption.assert_awaited_once()
    message.edit_text.assert_not_awaited()


@pytest.mark.asyncio
async def test_edit_callback_message_falls_back_when_text_edit_fails():
    message = MagicMock()
    message.photo = None
    message.document = None
    message.video = None
    message.animation = None
    message.edit_text = AsyncMock(
        side_effect=TelegramBadRequest(
            method="editMessageText",
            message="Bad Request: there is no text in the message to edit",
        )
    )
    message.edit_caption = AsyncMock()
    message.answer = AsyncMock()

    await edit_callback_message(message, "menu")

    message.answer.assert_awaited_once()
