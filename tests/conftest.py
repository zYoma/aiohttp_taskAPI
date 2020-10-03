import jwt
import peewee
import peewee_async
import pytest
from app import create_app
from task_manager.models import STATUS_LIST, Task, TaskLog, User, database
from task_manager.settings import JWT_SECRET


@pytest.fixture
async def app():
    app = await create_app()
    yield app


@pytest.fixture
def client(loop, aiohttp_client, app):
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture()
async def token(client, app):
    token_jwt = jwt.encode(
        {"username": 'ivan', "scopes": [f"username:ivan"]}, JWT_SECRET
    )
    yield token_jwt.decode()
    try:
        user = await app.objects.get(User, login='ivan')
    except peewee.DoesNotExist:
        pass
    else:
        await app.objects.delete(user)


@pytest.fixture
async def user(app):
    user, _ = await app.objects.create_or_get(User, login='ivan', password='123456')
    yield user
    await app.objects.delete(user)


@pytest.fixture
async def task(app, user):
    task = await app.objects.create(Task, user=user, name='Teting task', description='description', status='new')
    yield task
    await app.objects.delete(task)
