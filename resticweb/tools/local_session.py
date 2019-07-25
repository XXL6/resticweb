from sqlalchemy import create_engine, exc
from sqlalchemy.orm import sessionmaker


class LocalSession:
    def __enter__(self):
        engine = create_engine('sqlite:///resticweb/general.db')
        Session = sessionmaker(bind=engine)
        self.session = Session()
        return self.session

    def __exit__(self, type, value, traceback):
        self.session.close()
