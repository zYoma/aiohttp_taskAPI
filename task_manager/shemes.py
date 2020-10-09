import json
from datetime import datetime

from pydantic import BaseModel, Field, constr, validator


def orjson_dumps(v, *, default):
    return json.dumps(v, default=default, ensure_ascii=False)


class UserSchema(BaseModel):
    login: constr(max_length=50)
    password: constr(max_length=100)

    class Config:
        json_dumps = orjson_dumps

class FilterTask(BaseModel):
    status: constr(max_length=15) = None
    completion_at: str = None

    @validator('status')
    def check_status(cls, v):
        status_list = [None, 'new', 'planned', 'in_work', 'сompleted']
        if not v in status_list:
            raise ValueError('Не корректный статус! available values(new, planned, in_work, сompleted)')

        return v

    @validator('completion_at')
    def check_completion_at(cls, v):
        if v is not None:
            try:
                completion_at = datetime.strptime(v, '%d-%m-%Y')
            except ValueError:
                raise ValueError('incorrect completion_at format (%d-%m-%Y)')

            return completion_at

        return v

    class Config:
        json_dumps = orjson_dumps


class TaskSchema(FilterTask, BaseModel):
    user: int
    name: constr(max_length=50)
    description: constr()
    status: constr(max_length=15)

    class Config:
        json_dumps = orjson_dumps


class PutTaskSchema(FilterTask, BaseModel):
    user: int = None
    name: constr(max_length=50) = None
    description: constr() = None
    status: constr(max_length=15) = None

    class Config:
        json_dumps = orjson_dumps


class GetTaskSchema( BaseModel):
    user: int
    name: constr()
    description: constr()
    status: constr()
    completion_at: datetime = None

    class Config:
        json_dumps = orjson_dumps
