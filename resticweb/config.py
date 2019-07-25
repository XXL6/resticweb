# development config


class Config:
    SQLALCHEMY_BINDS = {
        # 'system':   'sqlite:///ub_system.db',
        'general':   'sqlite:///general.db'
        # 'backup':   'sqlite:///ub_backup.db'
    }
    SECRET_KEY = 'devkey'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False
