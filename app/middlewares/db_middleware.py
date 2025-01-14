# partially from https://github.com/aiogram/bot

from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, types
from aiogram.dispatcher.event.bases import CancelHandler
from aiogram.types import TelegramObject
from tortoise import BaseDBAsyncClient

from app.infrastructure.database.repo.chat import ChatRepo
from app.infrastructure.database.repo.report import ReportRepo
from app.infrastructure.database.repo.user import UserRepo
from app.services.settings import get_chat_settings
from app.utils.log import Logger

logger = Logger(__name__)


class DBMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        chat: types.Chat = data.get("event_chat", None)
        user: types.User = data.get("event_from_user", None)
        if isinstance(event, types.Message) and event.sender_chat:
            raise CancelHandler

        # TODO: need to pass db session here
        await self.setup_chat(data, user, chat)
        return await handler(event, data)

    async def setup_chat(
        self,
        data: dict,
        user: types.User,
        chat: types.Chat | None = None,
        session: BaseDBAsyncClient | None = None,
    ):
        try:
            chat_repo = ChatRepo(session)
            user_repo = UserRepo(session)
            report_repo = ReportRepo(session)

            user = await user_repo.get_or_create_from_tg_user(user)

            if chat and chat.type != "private":
                chat = await chat_repo.get_or_create_from_tg_chat(chat)
                data["chat_settings"] = await get_chat_settings(chat=chat)
        except Exception as e:
            logger.exception("troubles with db", exc_info=e)
            raise e

        data["user"] = user
        data["chat"] = chat
        data["chat_repo"] = chat_repo
        data["user_repo"] = user_repo
        data["report_repo"] = report_repo
