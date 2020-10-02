from datetime import datetime

import peewee
import peewee_async
import peeweedbevolve
import settings

database = peewee_async.PostgresqlDatabase(None)


class BaseModel(peewee.Model):

    class Meta:
        database = database


STATUS_LIST = (
    ('new', 'Новая'),
    ('planned', 'Запланированная'),
    ('in_work', 'В работе'),
    ('сompleted', 'Завершённая'),
)


class User(BaseModel):
    login = peewee.CharField(max_length=50, unique=True, verbose_name='Логин')
    password = peewee.CharField(max_length=100, verbose_name='Пароль')

    def __str__(self):
        return self.login


class Task(BaseModel):
    user = peewee.ForeignKeyField(
        User, on_delete='CASCADE', related_name='tasks', verbose_name='Пользователь')
    name = peewee.CharField(max_length=50, verbose_name='Название')
    description = peewee.TextField(verbose_name='Описание')
    created_at = peewee.DateTimeField(
        default=datetime.now, verbose_name='Дата создания')
    status = peewee.CharField(
        max_length=15, choices=STATUS_LIST, verbose_name='Статус')
    completion_at = peewee.DateTimeField(
        null=True, verbose_name='Дата завершения')

    def __str__(self):
        return self.name

    class Meta:
        order_by = ('created_at', )


class TaskLog(BaseModel):
    task = peewee.ForeignKeyField(
        Task, on_delete='CASCADE', related_name='task_logs', verbose_name='Задача')
    log = peewee.CharField(max_length=200, verbose_name='Лог')
    created_at = peewee.DateTimeField(
        default=datetime.now, verbose_name='Дата создания')

    def __str__(self):
        return self.log


if __name__ == '__main__':
    database.init(**settings.DATABASE)
    database.evolve()
