from task_manager.models import STATUS_LIST, Task, TaskLog, User


async def test_registration_without(client):
    # Нельзя зарегистрироваться не указав логин пароль.
    resp = await client.post(client.app.router['registration'].url_for())
    assert resp.status == 400
    assert 'incorrect data' in await resp.text()


async def test_registration(client, token):
    # Можем зарегистрироваься если указали логин и пароль.
    resp = await client.post(client.app.router['registration'].url_for(), data={'login': 'ivan', 'password': '123456'})
    assert resp.status == 200
    assert token in await resp.text()


async def test_get_token_without(client):
    # Пробуем получить токен не передав логин пароль.
    resp = await client.post(client.app.router['gen_token'].url_for())
    assert resp.status == 400
    assert 'auth_error' in await resp.text()


async def test_get_token(client, token):
    # Можем получить токен если переданы корректные данные.
    await client.post(client.app.router['registration'].url_for(), data={'login': 'ivan', 'password': '123456'})
    resp = await client.post(client.app.router['gen_token'].url_for(), data={'login': 'ivan', 'password': '123456'})
    assert resp.status == 200
    assert token in await resp.text()


async def test_create_task_without(client):
    # Не можем создать задачу без токена
    resp = await client.post(client.app.router['task'].url_for())
    assert resp.status == 401
    assert 'Authorization required' in await resp.text()

async def test_create_task(client, user, token):
    # Можем создать задачу, если передан токен и обязательные поля.
    resp = await client.post(client.app.router['task'].url_for(), data={
        'user': user,
        'name': 'New task',
        'description': 'Описание',
        'status': 'new',
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 201
    assert 'New task' in await resp.text()


async def test_update_task(client, token, task):
    # Пробуем изменить задачу.
    resp = await client.put(client.app.router['single_task'].url_for(id=str(task.id)), data={
        'name': 'Modifed name',
        'description': 'Update description',
        'status': 'new',
        'completion_at': '12-02-2020',
    }, headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    assert 'Modifed name' in await resp.text()

async def test_get_history(client, token, task):
    # Получаем историю изменений
    resp = await client.put(client.app.router['single_task'].url_for(id=str(task.id)), data={
        'description': 'Changed description',
        'completion_at': '11-11-2020',
    }, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(client.app.router['task_log'].url_for(id=str(task.id)),
                            headers={"Authorization": f"Bearer {token}"})
    assert resp.status == 200
    assert 'Changed description' in await resp.text()
    assert '11-11-2020' in await resp.text()
    assert len(await resp.json()) == 2
