from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
import resticweb.interfaces.repository_list as repository_interface
import resticweb.interfaces.repository_type as repository_type_interface
from resticweb.models.general import Repository, RepositoryType
from resticweb.engine_classes.class_name_map import get_class_from_name
from resticweb import db
import json
from .forms import AddRepositoryTypeForm, get_add_repository_form, EditRepositoryTypeForm, get_edit_repository_form
from resticweb.misc import job_queue
from resticweb.tools.job_build import JobBuilder
from resticweb.dictionary.resticweb_variables import Config
from resticweb.dictionary.resticweb_constants import System
import os
import resticweb.tools.job_callbacks as job_callbacks
import platform
from time import sleep
from threading import Thread
import humanize

repositories = Blueprint('repositories', '__name__')


@repositories.route(f'/{repositories.name}')
@repositories.route(f'/{repositories.name}/repository_list')
def repository_list():
    page = request.args.get('page', 1, type=int)
    repositories = Repository.query.paginate(page=page, per_page=40)
    return render_template('repositories/repository_list.html', repositories=repositories)


@repositories.route(f'/{repositories.name}/repository_list/<int:repository_id>')
def repository_snapshots(repository_id):
    snapshot_list = repository_interface.get_snapshots(repository_id)
    repository_name = repository_interface.get_repository_name(repository_id)
    return render_template('repositories/snapshot_list.html', snapshots=snapshot_list, repository_name=repository_name)


@repositories.route(f'/{repositories.name}/repository_list/snapshot_list/<string:snapshot_id>')
def snapshot_list(snapshot_id):
    snapshot = repository_interface.get_snapshot_info(snapshot_id)
    repository = Repository.query.filter_by(id=snapshot.repository_id).first()
    snapshot_objects = repository_interface.get_snapshot_objects(snapshot_id, repository.cache_repo)
    node_list = []
    # following is a node structure that is intended to be understood by the Javascript
    # JStree plugin
    for snapshot_object in snapshot_objects:
        if snapshot_object['struct_type'] == 'snapshot':
            node_list.append({
                'id': 'snapshot_root',
                'parent': '#',
                'text': snapshot.snap_short_id + ' - ' + snapshot.snap_time.strftime(System.DEFAULT_TIME_FORMAT),
                'state': {
                    'opened': True
                }
            })
        elif snapshot_object['struct_type'] == 'node':
            node_id = snapshot_object['path'].replace(' ', '').replace('/', '')
            node_parent = snapshot_object['path'].replace(' ', '').split('/')[1:]
            if len(node_parent) == 1:
                node_parent = 'snapshot_root'
            else:
                node_parent = ''.join(node_parent[:-1])
            li_attr = {'item_path': snapshot_object['path']}
            node_list.append({
                'id': node_id,
                'parent': node_parent,
                'li_attr': li_attr,
                'text': snapshot_object['name'],
                'icon': 'jstree-file' if snapshot_object['type'] == 'file' else 'jstree-folder'
            })
    return render_template('repositories/snapshot_viewer.html', snapshot_id=snapshot_id, node_list=json.dumps(node_list))


@repositories.route(f'/{repositories.name}/repository_list/_get_repository_info')
def get_repository_info():
    info_dict = {}
    repository_id = request.args.get('id', 0, type=int)
    info_dict = repository_interface.get_info(repository_id)
    repo_size = info_dict['data'].get('total_size')
    if repo_size:
        info_dict['data']['total_size'] = humanize.naturalsize(repo_size, binary=True)
    return render_template('sidebar/repository_list.html', info_dict=info_dict)


@repositories.route(f'/{repositories.name}/repository_list/_get_snapshot_info')
def get_snapshot_info():
    info_dict = {}
    snapshot_id = request.args.get('id', 'None', type=str)
    info_dict = repository_interface.get_snapshot_info(snapshot_id)
    return render_template('sidebar/snapshot_list.html', info_dict=info_dict)


@repositories.route(f'/{repositories.name}/repository_list/_forget_snapshot', methods=['POST'])
def forget_snapshot():
    snapshot_id = request.get_json().get('item_id')
    snapshot_info = repository_interface.get_snapshot_info(snapshot_id)
    job_build = JobBuilder(job_class='forget', job_name='Snapshot Forget', 
        parameters=dict(snapshot_id=snapshot_id, repository=snapshot_info.repository_id))
    result = job_build.run_job()
    '''
    if result == 0:
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
    else:
        return json.dumps({'success': False, 'errormsg' : f'Unable to forget snapshot. {result}'}), 500, {'ContentType': 'application/json'}
    '''
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@repositories.route(f'/{repositories.name}/repository_list/_get_repository_status')
def get_repository_status():
    repository_id = request.args.get('id', 0, type=int)
    status = repository_interface.get_repository_status(repository_id)
    return json.dumps({'data': status, 'name': 'status', 'id': repository_id})


@repositories.route(f'/{repositories.name}/repository_list/_add', methods=['GET', 'POST'])
def choose_repository_type():
    if request.method == 'POST':
        repository_type = request.form['repository-type-select']
        return redirect(url_for('repositories.add_repository', repository_type=repository_type))
    available_repository_types = []
    for item in repository_type_interface.get_repository_types():
        available_repository_types.append((item['id'], item['name']))
    return render_template("repositories/choose_repository_type.html", available_repository_types=available_repository_types)


@repositories.route(f'/{repositories.name}/repository_list/_add/<int:repository_type>', methods=['GET', 'POST'])
def add_repository(repository_type):
    type_info = repository_type_interface.get_repository_type(repository_type)
    form = get_add_repository_form(type_info['internal_binding'])
    if form.validate_on_submit():
        new_info = {}
        new_info['parameters'] = {}
        address = repo_address_format(type_info['internal_binding'], form)
        global_credentials = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit':
                if type(item).__name__ == 'RWCredentialField':
                    global_credentials[item.id] = item.data
                else:
                    new_info[item.id] = item.data
                    if item.id != 'repo_password' \
                            and item.id != 'description' \
                            and item.id != 'name' \
                            and item.id != 'cache_repo' \
                            and item.id != 'repository_id':
                        new_info['parameters'][item.id] = item.data

        new_info['repository_type_id'] = repository_type
        job_builder = JobBuilder(job_class='repository', job_name=f'Repository Create: {new_info["name"]}', parameters=dict(
                address=address,
                repo_password=form.repo_password.data,
                field_dict=new_info,
                global_credentials=global_credentials if len(global_credentials) > 0 else None
            ))
        job_builder.run_job()
        flash("Repository job added to queue", category='success')
        return redirect(url_for('repositories.repository_list'))
    return render_template(f"repositories/repository_list_add_{repository_type}.html", form=form)


def repo_address_format(repository_type, form):
    if repository_type == 'local':
        if platform.system() == 'Windows':
            if form.address.data[0] == '/':
                form.address.data = form.address.data[1:]
            form.address.data = form.address.data.replace('/', os.sep)
        return form.address.data
    elif repository_type == 'amazons3':
        address = f's3:s3.amazonaws.com/{form.bucket_name.data}'
        return address
    elif repository_type == 'rclone':
        address = form.rclone_address.data
        if 'rclone:' not in address[0:7]:
            address = 'rclone:' + address
        return address
    else:
        return None

@repositories.route(f'/{repositories.name}/repository_list/_edit/<int:repository_id>', methods=['GET', 'POST'])
def edit_repository(repository_id):
    repository = Repository.query.filter_by(id=repository_id).first()
    repository_type = RepositoryType.query.filter_by(id=repository.repository_type_id).first()
    form = get_edit_repository_form(repository_type.internal_binding)
    if form.validate_on_submit():
        address = repo_address_format(repository_type.internal_binding, form)
        sync_db = False
        unsync_db = False
        # if the cache_repo value has been changed then we want to sync the db
        # by either adding all the snapshot objects or deleting them from
        # the database
        if not repository.cache_repo and form.cache_repo.data:
            sync_db = True
        elif repository.cache_repo and not form.cache_repo.data:
            unsync_db = True
        parameters = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit':
                if item.id != 'description' \
                        and item.id != 'name' \
                        and item.id != 'cache_repo' \
                        and item.id != 'repository_id':
                    parameters[item.id] = item.data
        update_info = dict(
            name=form.name.data,
            address=address,
            parameters=parameters,
            description=form.description.data,
            cache_repo=form.cache_repo.data,
            concurrent_uses=form.concurrent_uses.data,
            timeout=form.timeout.data
        )
        repository_interface.update_repository(update_info, form.repository_id.data, sync_db, unsync_db)
        if sync_db:
            flash("Repository edited successfully. Sync job has been added.", category='success')
        elif unsync_db:
            flash("Repository edited successfully. Current snapshot objects will be removed.", category='success')
        else:
            flash("Repository edited successfully", category='success')
        return redirect(url_for('repositories.repository_list'))
    else:
        form.repository_id.data = repository.id
        form.cache_repo.data = repository.cache_repo
        form.description.data = repository.description
        form.name.data = repository.name
        form.concurrent_uses.data = repository.concurrent_uses
        form.timeout.data = repository.timeout
        form.set_current_data(json.loads(repository.parameters))
    return render_template(f"repositories/repository_list_edit_{repository.repository_type_id}.html", form=form)


@repositories.route(f'/{repositories.name}/repository_list/_delete', methods=['GET', 'POST'])
def delete_repositories():
    item_ids = request.get_json().get('item_ids')
    try:
        repository_interface.delete_repositories(item_ids)
    except Exception as e:
        flash(f"Items not removed: {e}", category='error')
        return json.dumps({'success': True}), 500, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@repositories.route(f'/{repositories.name}/repository_types/_add', methods=['GET', 'POST'])
def add_repository_type():
    form = AddRepositoryTypeForm()
    if form.validate_on_submit():
        new_info = {}
        new_info['name'] = form.name.data
        new_info['type'] = form.type.data
        new_info['description'] = form.description.data
        new_info['internal_binding'] = form.internal_binding.data
        repository_type_interface.add_repository_type(new_info)
        flash("Repository type has been added", category='success')
        return redirect(url_for('repositories.repository_types'))
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template("repositories/repository_types_edit.html", form=form)


@repositories.route(f'/{repositories.name}/repository_types')
def repository_types():
    page = request.args.get('page', 1, type=int)
    items = RepositoryType.query.order_by(RepositoryType.name.desc()).paginate(page=page, per_page=40)
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template("repositories/repository_types.html", items=items)


@repositories.route(f'/{repositories.name}/repository_types/_edit/<int:type_id>', methods=['GET', 'POST'])
def edit_repository_type(type_id):
    form = EditRepositoryTypeForm()
    if form.validate_on_submit():
        new_info = {}
        new_info['name'] = form.name.data
        new_info['type'] = form.type.data
        new_info['description'] = form.description.data
        new_info['internal_binding'] = form.internal_binding.data
        repository_type_interface.set_repository_type(type_id, new_info)
        flash("Repository type has been updated", category='success')
        return redirect(url_for('repositories.repository_types'))
    else:
        type = repository_type_interface.get_repository_type(type_id)
        form.internal_binding.default = type['internal_binding']
        form.process()
        if type:
            form.name.data = type['name']
            form.type.data = type['type']
            form.description.data = type['description']
            form.repository_type_id.data = type['id']
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template("repositories/repository_types_edit.html", form=form)


@repositories.route(f'/{repositories.name}/repository_types/_get_type_info')
def get_type_info():
    info_dict = {}
    repository_type_id = request.args.get('id', 0, type=int)
    info_dict['description'] = repository_type_interface.get_repository_type(repository_type_id)['description']
    info_dict['internal_binding'] = repository_type_interface.get_repository_type(repository_type_id)['internal_binding']
    return render_template('sidebar/repository_types.html', info_dict=info_dict)


@repositories.route(f'/{repositories.name}/repository_types/_delete', methods=['POST'])
def delete_location_types():
    type_list = request.get_json().get('item_ids')
    for type in type_list:
        repository_type_interface.delete_repository_type(type)
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}