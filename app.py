import aiohttp_debugtoolbar
import peewee_async
from aiohttp import web
from aiohttp_jwt import JWTMiddleware
from models import database
from settings import DATABASE, JWT_SECRET, logger
from urls import setup_routes

jwt_middleware = JWTMiddleware(
    JWT_SECRET, request_property="user", credentials_required=False
)


async def create_app():
    app = web.Application(
        middlewares=[jwt_middleware, aiohttp_debugtoolbar.middleware])
    aiohttp_debugtoolbar.setup(
        app, intercept_redirects=False, check_host=False)
    setup_routes(app)
    app.logger = logger
    app.on_startup.append(on_start)
    app.on_cleanup.append(on_shutdown)
    return app


async def on_start(app):
    database.init(**DATABASE)
    app.database = database
    app.database.set_allow_sync(False)
    app.objects = peewee_async.Manager(app.database)


async def on_shutdown(app):
    await app.objects.close()
    await app.shutdown()
