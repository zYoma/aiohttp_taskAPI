import hashlib
from datetime import datetime

import jwt
import peewee
from aiohttp import web
from aiohttp_jwt import login_required

from settings import JWT_SECRET, PASS_SALT
from models import User, Task, TaskLog, STATUS_LIST


class TaskLogs(web.View):

    @login_required
    async def get(self):
        """ Отдает историю изменений определенной задачи. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'})

        logs = await self.app.objects.execute(TaskLog.select().where(TaskLog.task == task))
        return web.json_response(await self.serializer(logs), status=200)

    @staticmethod
    async def serializer(logs):
        """ Формируем словарь для сериализации. """
        result = []
        for log in logs:
            task_log = {'date': str(log.created_at), 'log': log.log}
            result.append(task_log)

        return result

    async def get_task(self):
        """ Пытаемся получить задачу, если такой нет, обрабатываем исключение. """
        try:
            task = await self.app.objects.get(Task, id=self.id)
        except peewee.DoesNotExist:
            return None
        else:
            return task


class SingleTaskAPI(web.View):

    @login_required
    async def get(self):
        """ Отдаем одну задачу по id. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'})
        return web.json_response(await serializer(task), status=200)

    @login_required
    async def put(self):
        """ Изменить задачу по id. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'}, status=400)

        data = await self.request.post()
        self.name = data.get('name')
        self.description = data.get('description')
        self.status = data.get('status')
        self.completion_at = data.get('completion_at')
        if self.status:
            check_status = await validate_status(self.status)
            if not check_status:
                return web.json_response({'error': 'incorrect status. available values(new, planned, in_work, сompleted)'}, status=400)

        if self.completion_at:
            is_valid_completion_at = await validate_completion_at(self.completion_at)
            if not is_valid_completion_at:
                return web.json_response({'error': 'incorrect completion_at format (%d-%m-%Y)'}, status=400)

        await self.update_fields(task)
        updeted_task = await self.get_task()
        return web.json_response(await serializer(updeted_task), status=200)

    @login_required
    async def delete(self):
        """ Удаляем задачу по id. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'}, status=400)
        await self.app.objects.delete(task)
        self.app.logger.debug(f'Удалена задача {task.name}')
        return web.json_response({'status': 'deleted'}, status=204)

    async def update_fields(self, task):
        """ Метод обновляет те свойства, которые изменились.
            Формируем словарь feilds всех свойств и их значений.
            Обходим все элементы словаря и обновляем те свойства, которые поменялись.
            Записывает в TaskLog историю изменений.
        """
        feilds = {
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'completion_at': self.completion_at
        }
        for key, value in feilds.items():
            if value and value != str(getattr(task, key)):
                await self.app.objects.execute(Task.update(**{key: value}).where(Task.id == self.id))
                await self.app.objects.create(
                    TaskLog,
                    task=task,
                    log=f'Значение поля {key} изменено на {value}',
                )
                self.app.logger.debug(f'У задачи {task.name} изменено значение поля {key} на {value}')

    async def get_task(self):
        try:
            task = await self.app.objects.get(Task, id=self.id)
        except peewee.DoesNotExist:
            return None
        else:
            return task


class TaskAPI(web.View):

    @login_required
    async def get(self):
        """ Выводим все задачи пользователя. 
            Если в запросе есть параметры status,completion_at, 
            фильтруем задачи по ним.
        """
        self.app = self.request.app
        data = self.request.query
        status = data.get('status')
        completion_at = data.get('completion_at')

        user = await self.get_user()
        tasks = await self.app.objects.execute(Task.select().where(Task.user == user))

        if status:
            check_status = await validate_status(status)
            if not check_status:
                return web.json_response({'error': 'incorrect status field'}, status=400)

            tasks = [task for task in tasks if task.status == status]

        if completion_at:
            is_valid_completion_at = await validate_completion_at(completion_at)
            if not is_valid_completion_at:
                return web.json_response({'error': 'incorrect completion_at format (%d-%m-%Y)'}, status=400)

            tasks = [
                task for task in tasks if task.completion_at is not None and task.completion_at <= is_valid_completion_at]

        result_list = []
        for task in tasks:
            obj = await serializer(task)
            result_list.append(obj)

        return web.json_response(result_list, status=200)

    @login_required
    async def post(self):
        """ Создание задачи. Валидация данных. """
        self.app = self.request.app
        data = await self.request.post()
        name = data.get('name')
        description = data.get('description')
        status = data.get('status')
        completion_at = data.get('completion_at')

        is_valid_atributes = await self.validate_atributes([name, description, status])
        if not is_valid_atributes:
            return web.json_response({'error': 'incorrect data'}, status=400)

        check_status = await validate_status(status)
        if not check_status:
            return web.json_response({'error': 'incorrect status. available values(new, planned, in_work, сompleted)'}, status=400)

        if completion_at:
            is_valid_completion_at = await validate_completion_at(completion_at)
            if not is_valid_completion_at:
                return web.json_response({'error': 'incorrect completion_at format (%d-%m-%Y)'}, status=400)

        user = await self.get_user()

        new_task = await self.app.objects.create(
            Task,
            user=user,
            name=name,
            description=description,
            status=status,
            completion_at=is_valid_completion_at if completion_at else None,
        )
        self.app.logger.debug(f'Создана задача {new_task}.')
        return web.json_response(await serializer(new_task), status=201)

    async def get_user(self):
        """ Получаем логин пользователя из словаря request
            Возвращаем объект User с данным логином.
        """
        username = self.request["user"].get("username")
        return await self.app.objects.get(User, login=username)

    @staticmethod
    async def validate_atributes(atribute_list):
        """ Проверяем что присутсвуют все обяхательные поля. """
        for atribute in atribute_list:
            if atribute is None or atribute == '':
                return False

        return True


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


class GetToken(web.View):
    async def post(self):
        """ Если предоставленные данные корректны, выдаем JWT токен. """
        self.app = self.request.app
        data = await self.request.post()
        self.login = data.get('login')
        self.password = data.get('password')
        if self.login is None or self.password is None:
            return web.json_response({'auth_error': 'incorrect data'}, status=400)
        user = await self.check_user()
        if user:
            token = await create_jwt(user)
            self.app.logger.debug(f'Пользователь {user.login} запросил токен.')
            return web.json_response({'access_token': token.decode()}, status=200)
        else:
            return web.json_response({'auth_error': 'incorrect data'}, status=400)

    async def check_user(self):
        """ Проверяем существует ли пользователь с указанными данными. """
        pass_hash = await gen_hash(self.password)
        try:
            user = await self.app.objects.get(User, login=self.login, password=pass_hash)
        except peewee.DoesNotExist:
            return False
        else:
            return user


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


class Register(web.View):
    async def post(self):
        """ Регистрируем пользователя если получили валидные данные.
            Сразу выдаем токен пользователю.
        """
        app = self.request.app
        data = await self.request.post()
        self.login = data.get('login')
        self.password = data.get('password')
        error = await self.validate_login_and_password()
        if error:
            return web.json_response({'error': error}, status=400)

        pass_hash = await gen_hash(self.password)
        try:
            new_user = await app.objects.create(User, login=self.login, password=pass_hash)
        except peewee.IntegrityError:
            return web.json_response({'error': 'login alrede exists'}, status=400)
        else:
            app.logger.debug(f'Зарегистрирован новый пользователь {new_user}')
            token = await create_jwt(new_user)
            return web.json_response({'access_token': token.decode()}, status=200)

    async def validate_login_and_password(self):
        """ Простейшая валидация логина и пароля. """
        error = None
        if self.login is None or self.password is None or self.login == '' or self.password == '':
            error = 'incorrect data'

        return error
