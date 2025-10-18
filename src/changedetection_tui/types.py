from typing import Literal
from pydantic import BaseModel, RootModel


class ApiListWatch(BaseModel):
    last_changed: int
    last_checked: int
    last_error: str | Literal[False]
    title: str | None
    url: str
    viewed: bool

    def title_or_url(self) -> str:
        return self.title or self.url


class ApiListWatches(RootModel[dict[str, ApiListWatch]]):
    pass


class ApiWatch(ApiListWatch):
    last_viewed: int
    uuid: str


class ApiTag(BaseModel):
    date_created: int
    notification_muted: bool
    title: str
    uuid: str


class ApiListTags(RootModel[dict[str, ApiTag]]):
    pass
