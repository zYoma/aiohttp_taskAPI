import hashlib
from datetime import datetime

import jwt

from .models import STATUS_LIST
from .settings import JWT_SECRET, PASS_SALT


async def validate_completion_at(completion_at):
    """ Проверяем что дата завершения введена в нужном формате. """
    try:
        completion_at = datetime.strptime(completion_at, '%d-%m-%Y')
    except ValueError:
        return False
    else:
        return completion_at


async def validate_status(status):
    """ Проверка полученного статуса. Статус должен быть одним из списка STATUS_LIST. """
    status_list = [i[0] for i in STATUS_LIST]
    if not status in status_list:
        return False

    return True


async def serializer(task):
    """ Формируем словарь для сериализации. """
    task_dict = {'id': task.id, 'name': task.name,
                 'description': task.description, 'status': task.status}
    if task.completion_at:
        task_dict.update(
            {"completion_at": task.completion_at.strftime('%d-%m-%Y')})
    return task_dict


async def gen_hash(password: str):
    """ Хшируем пароль с солью. """
    str2hash = password + PASS_SALT
    result = hashlib.md5(str2hash.encode())
    return result.hexdigest()


async def create_jwt(user):
    """ Создаем токен, замешивая логин с секретом. """
    return jwt.encode(
        {"username": user.login, "scopes": [f"username:{user.login}"]}, JWT_SECRET
    )
