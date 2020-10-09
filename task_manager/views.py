
import peewee
from aiohttp import web
from aiohttp_jwt import login_required

from .models import Task, TaskLog, User
from .shemes import FilterTask, GetTaskSchema, PutTaskSchema, TaskSchema
from .utils import (create_jwt, gen_hash, serializer, validate_completion_at,
                    validate_status)


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

        data = TaskSchema(**task.__dict__['__data__'])
        return web.json_response(text=data.json(), status=200)

    @login_required
    async def put(self):
        """ Изменить задачу по id. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'}, status=400)

        user = await self.get_user()
        if user.id != task.user_id:
            return web.json_response({'error': 'Access is denied'}, status=403)

        data = await self.request.post()
        self.name = data.get('name')
        self.description = data.get('description')
        self.status = data.get('status')
        self.completion_at = data.get('completion_at')

        data = PutTaskSchema(
            user=user.id,
            name=self.name, 
            description=self.description,
            status=self.status,
            completion_at=self.completion_at,
        )
        
        await self.update_fields(task)
        updeted_task = await self.get_task()
        return web.json_response(data.json(), status=200)

    @login_required
    async def delete(self):
        """ Удаляем задачу по id. """
        self.id = self.request.match_info['id']
        self.app = self.request.app
        task = await self.get_task()
        if task is None:
            return web.json_response({'error': 'task not found'}, status=400)
        user = await self.get_user()
        if user.id != task.user_id:
            return web.json_response({'error': 'Access is denied'}, status=403)

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
            task = await self.app.objects.get(Task.select().join(User).where(Task.id == self.id))
        except peewee.DoesNotExist:
            return None
        else:
            return task

    async def get_user(self):
        """ Получаем логин пользователя из словаря request
            Возвращаем объект User с данным логином.
        """
        username = self.request["user"].get("username")
        return await self.app.objects.get(User, login=username)


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
        tasks = status_query = completion_at_query = Task.select().where(Task.user == user)

        data = FilterTask(
            status=status,
            completion_at=completion_at,
        )
        if status:
            status_query = Task.select().where(Task.status == status, Task.user == user)

        if completion_at:
            completion_at_query = Task.select().where(
                Task.completion_at >= data['completion_at'], Task.user == user)

        query = tasks & status_query & completion_at_query
        tasks = await self.app.objects.execute(query)

        result_list = []
        for task in tasks:
            obj = GetTaskSchema(**task.__dict__['__data__'])
            result_list.append(obj.json())

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

        user = await self.get_user()
        data = TaskSchema(
            user=user.id,
            name=name, 
            description=description,
            status=status,
            completion_at=completion_at,
        )
        
        new_task = await self.app.objects.create(
            Task,
            **data.dict()
        )
        
        self.app.logger.debug(f'Создана задача {new_task}.')
        return web.json_response(data.json(), status=201)

    async def get_user(self):
        """ Получаем логин пользователя из словаря request
            Возвращаем объект User с данным логином.
        """
        username = self.request["user"].get("username")
        return await self.app.objects.get(User, login=username)


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
