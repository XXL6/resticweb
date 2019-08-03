from flask import Flask, render_template
from resticweb.config import Config
from resticweb import db, login_manager, bcrypt, logger
from resticweb.engine_configure import configure_engine
from resticweb.misc.credential_manager import credential_manager
from resticweb.dictionary.resticweb_exceptions import NoEngineAvailable
from resticweb.init_db import init_db
import os


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        init_db()
    credential_manager.assign_session(db.session)
    from resticweb.blueprints.main.routes import main
    from resticweb.blueprints.jobs.routes import jobs
    from resticweb.blueprints.users.routes import users
    from resticweb.blueprints.backup.routes import backup
    from resticweb.blueprints.restore.routes import restore
    from resticweb.blueprints.system.routes import system
    from resticweb.blueprints.repositories.routes import repositories
    app.register_blueprint(main)
    app.register_blueprint(jobs)
    app.register_blueprint(users)
    app.register_blueprint(backup)
    app.register_blueprint(restore)
    app.register_blueprint(system)
    app.register_blueprint(repositories)
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(403, unauthorized_access)
    app.register_error_handler(500, server_error)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    try:
        configure_engine()
    except NoEngineAvailable:
        logger.error(f'Unable to create and start the application.\n\
            Backup engine not found in the system.\n\
            Either have Restic in the PATH or add the executable \
            in the .{os.sep}resticweb{os.sep}engine folder')
        print(f'''
            Unable to create and start the application.\n\
            Backup engine not found in the system.\n\
            Either have Restic in the PATH or add the executable \
            in the .{os.sep}resticweb{os.sep}engine folder
            ''')
        exit(1)
        
    logger.info('App created')
    return app

def page_not_found(e):
    return render_template('errors/404.html'), 404

def unauthorized_access(e):
    return render_template('errors/403.html'), 403

def server_error(e):
    return render_template('errors/500.html'), 500