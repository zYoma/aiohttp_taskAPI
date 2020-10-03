import aiohttp_debugtoolbar
import peewee_async
from aiohttp import web
from aiohttp_jwt import JWTMiddleware
from task_manager.models import database
from task_manager.settings import DATABASE, DEBUG, JWT_SECRET, logger
from task_manager.urls import setup_routes

jwt_middleware = JWTMiddleware(
    JWT_SECRET, request_property="user", credentials_required=False
)

async def create_app():
    middlewares = [jwt_middleware]
    
    middlewares.append(aiohttp_debugtoolbar.middleware)
    app = web.Application(middlewares=middlewares)
    
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
    if DEBUG:
        import aioreloader
        aioreloader.start()


async def on_shutdown(app):
    await app.objects.close()
    await app.shutdown()

if __name__=='__main__' and DEBUG:
    from task_manager.settings import HOST, PORT
    web.run_app(create_app(), host=HOST, port=PORT)
