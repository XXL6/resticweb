from flask import render_template, Blueprint, url_for, request, current_app
from flask_login import login_required, current_user
from resticweb import process_manager
import markdown2
import os

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

# serves a specified markdown help page from the templates/help_pages folder
# using the markdown2 plugin. Not sure how safe this is, but misaka wasn't
# working due to compilation errors
@main.route('/_get_help_page/<string:help_page>', methods=['GET'])
def get_help_page(help_page):
    page_location = os.path.join(os.path.dirname(current_app.instance_path), 'resticweb', 'templates', 'help_pages')
    return markdown2.markdown_path(f'{page_location}/{help_page}.md')
