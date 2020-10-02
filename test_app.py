import pytest
import jwt

from app import create_app
from models import User, Task, TaskLog, STATUS_LIST
from settings import JWT_SECRET


@pytest.fixture
async def app():
    app = await create_app()
    yield app


@pytest.fixture
def client(loop, aiohttp_client, app):
    return loop.run_until_complete(aiohttp_client(app))


@pytest.fixture()
async def token(client, app):
    print("setup")
    await client.post('/register', data={'login': 'ivan', 'password': '123456'})
    token_jwt = jwt.encode(
        {"username": 'ivan', "scopes": [f"username:ivan"]}, JWT_SECRET
    )
    yield token_jwt.decode()
    print("teardown")


@pytest.fixture
async def user(app):
    user = await app.objects.create_or_get(User, login='ivan', password='123456')
    yield user


async def test_registration(client):
    """ Проверяем, можем ли мы зарегистрироваться.
        Проверяем наличие обязательных данных.
    """
    resp = await client.post('/register')
    assert resp.status == 400
    assert 'incorrect data' in await resp.text()

    resp = await client.post('/register', data={'login': 'ivan'})
    assert resp.status == 400
    assert 'incorrect data' in await resp.text()


async def test_get_token(client, token):
    # Пробуем получить токен
    resp = await client.post('/get-token')
    assert resp.status == 400
    assert 'auth_error' in await resp.text()

    resp = await client.post('/get-token', data={'login': 'ivan', 'password': '123456'})
    assert resp.status == 200
    assert token in await resp.text()


async def test_create_task(client, token, app, user):
    # Не можем создать без токена
    resp = await client.post('/task')
    assert resp.status == 401
    assert 'Authorization required' in await resp.text()

    resp = await client.post('/task', data={
        'user': user,
        'name': 'New task',
        'description': 'Описание',
        'status': 'new',
    }, headers={"Authorization": f"Bearer {token}"})
    task_json = await resp.json()
    task_id = task_json['id']
    assert resp.status == 201
    assert 'New task' in await resp.text()

    # Изменяем задачу
    resp = await client.put(f'/task/{task_id}', data={
        'user': user,
        'name': 'Modifed name',
        'description': 'Update description',
        'status': 'new',
        'completion_at': '12-02-2020',
    }, headers={"Authorization": f"Bearer {token}"})
    html_text = await resp.text()

    assert resp.status == 200
    assert 'Modifed name' in html_text

    # Получаем историю изменений
    resp = await client.get(f'/task/{task_id}/log',
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    assert 'completion_at' in await resp.text()
    assert 'description' in await resp.text()
