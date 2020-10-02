from views import GetToken, Register, TaskAPI, SingleTaskAPI, TaskLogs


def setup_routes(app):
    app.router.add_route('POST', '/get-token', GetToken, name='gen_token')
    app.router.add_route('POST', '/register', Register, name='registration')
    app.router.add_route('GET', '/task/{id}/log', TaskLogs, name='task_log')
    app.router.add_route('*', '/task/{id}', SingleTaskAPI, name='single_task')
    app.router.add_route('*', '/task', TaskAPI, name='task')
