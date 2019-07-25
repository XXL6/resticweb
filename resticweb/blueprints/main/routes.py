from flask import render_template, Blueprint, url_for, request
from flask_login import login_required, current_user
from resticweb import process_manager

main = Blueprint('main', '__name__')


@main.route('/')
@main.route('/dashboard')
@main.route('/home')
# commented out during development
# @login_required
def home():
    return render_template('main.html')


@main.route('/shutdown')
def shutdown():
    shutdown_server()
    return "Server has been shut down"


def shutdown_server():
    func = request.environ.get('werkzeug.server.shutdown')
    if func is None:
        raise RuntimeError('Not running with the Werkzeug Server')
    process_manager.__exit__()
    func()
