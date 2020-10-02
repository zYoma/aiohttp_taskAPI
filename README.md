# aiohttp_taskAPI
#### Персонализированный сервис task manager, позволяющий пользователю ставить себе задачи, отражать в системе изменение их статуса и просматривать историю задач.

### Стек:
- aioHTTP
- aiohttp_jwt
- PostgreSQL
- peewee_async
- gunicorn
- docker
- pytest-aiohttp

### Функциональные возможности:
Пользователь может зарегистрироваться в сервисе задав пару логин-пароль
В системе может существовать много пользователей
Пользователь может авторизоваться в сервисе предоставив пару логин-пароль и получив в ответе токен
Пользователь видит только свои задачи
Пользователь может создать себе задачу. Задача должна как минимум содержать следующие данные:
(*) - обязательные поля
 - *Название(name)
 - *Описание(description)
 - *Статус(status) - один из Новая, Запланированная, в Работе, Завершённая
 - Планируемое дата завершения (completion_at)
Пользователь может менять статус задачи на любой из данного набора
Пользователь может менять планируемое время завершения, название и описание
Пользователь может получить список задач своих задач, с возможностью фильтрации по статусу и планируемому времени завершения
Есть возможность просмотреть историю изменений задачи (названия, описания, статуса, времени завершения)

### Запуск из контейнера:
``` docker-compose up ```

Необходимо создать файл **.env** с переменными окружения:
``` 
JWT_SECRET=секрет для генерации токенов
DB_HOST=db
DB=postgres
DB_USER=postgres
DB_PASSWORD=postgres
PASS_SALT=соль для хеширования паролей
```

Приложение будет доступно на стандартном **80** порту.

### При первом запуске необходимо сделать создать БД командой:
``` docker-compose run --rm aiohttp python models.py ```

### Для запуска тестов:
``` docker-compose run --rm aiohttp pytest ```

### Доступные методы:
```
/register   (POST)
/get-token   (POST)
/task  (GET, POST)
/task/{id}  (GET, POST, PUT, DELETE)
/task/{id}/log (GET)
```

### Пример запроса к API:
```
    import requests
    
    api = 'http://127.0.0.1/task'
    data = {
         'name': 'Новая задача',
         'description': 'Описание задачи',
         'status': 'new',
         'completion_at': '02-10-2020',
     }
     headers = {'Authorization': 'Bearer ваш_токен'}
     r = requests.post(api, data=data,  headers=headers)
```
### Создание редактирование и просмотр своих задач доступен только зарегистрированным пользователям. Для регистрации необходимо выполнить POST запрос с логином и паролем (login, password). В ответном сообщении прийдет токен который необходимо использовать в заголовке всем запросов.

### Доступна фильтрация задач по статусу и времени завершения. Для фильтрации необходимо передать доп. GET параметры *status* и *completion_at*.
```
/task/{id}?status=new&completion_at=02-10-2020
```