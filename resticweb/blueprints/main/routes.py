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

# serves a specified markdown help page from the templates/help_pages folder
# and runs it through the help_template.html filter which actually
# renders the markdown
@main.route('/_get_help_page/<string:help_page>', methods=['GET'])
def get_help_page(help_page):
    return render_template(f'help_pages/help_template.html', md_content=render_template(f'help_pages/{help_page}.md'))
