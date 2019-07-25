import os
from resticweb.models.general import RepositoryType
from resticweb.tools.local_session import LocalSession

def get_repository_types():
    return_list = []
    with LocalSession() as session:
        types = session.query(RepositoryType).order_by(RepositoryType.name.desc())
        for type in types:
            return_list.append(dict(
                id=type.id,
                name=type.name,
                type=type.type,
                description=type.description
            ))
    return return_list


def get_repository_type(id):
    return_dict = None
    with LocalSession() as session:
        type = session.query(RepositoryType).filter_by(id=id).first()
        if type:
            return_dict = dict(
                id=type.id,
                name=type.name,
                type=type.type,
                description=type.description
            )
    return return_dict


def add_repository_type(info):
    with LocalSession() as session:
        type = (
            RepositoryType(
                name=info['name'],
                type=info['type'],
                description=info.get('description')
            )
        )
        session.add(type)
        session.commit()


def set_repository_type(id, info):
    with LocalSession() as session:
        type = session.query(RepositoryType).filter_by(id=id).first()
        if type:
            type.name = info.get('name')
            type.type = info.get('type')
            type.description = info.get('description')
            session.commit()


def delete_repository_type(id):
    with LocalSession() as session:
        session.query(RepositoryType).filter_by(id=id).delete()
        session.commit()