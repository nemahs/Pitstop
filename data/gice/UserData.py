from datetime import datetime

from pydantic import Field

from data.data_source import UserData


class GICEUserData(UserData):
    """
    Docstring for UserData
    """

    sub: int
    name: str
    username: str
    nickname: str | None
    pri_grp: int
    grp: list[int] | int | None = None
    client_id: str
    scope: list[str] | str
    exp: datetime
    iat: datetime
    id: int = Field(..., alias="sub")