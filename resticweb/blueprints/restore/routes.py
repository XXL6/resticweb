from flask import render_template, Blueprint, request, flash, redirect, url_for
from resticweb.models.general import Repository
import resticweb.interfaces.repository_list as repository_interface
import resticweb.interfaces.repository as repository_engine_interface
from resticweb.dictionary.resticweb_constants import System
import json
from .forms import RestoreFilesForm
import platform
from resticweb.tools import filesystem_tools
from resticweb.tools.job_build import JobBuilder
import os

restore = Blueprint('restore', '__name__')


@restore.route(f'/{restore.name}/repositories')
def repositories():
    page = request.args.get('page', 1, type=int)
    repositories = Repository.query.paginate(page=page, per_page=40)
    return render_template('restore/repositories.html', repositories=repositories)


@restore.route(f'/{restore.name}/repositories/<int:repository_id>')
def repository_snapshots(repository_id):
    if repository_interface.get_repository_status(repository_id) != 'Online':
        flash('Cannot open an offline repository in restore mode', category='error')
        return redirect(url_for('restore.repositories'))
    snapshot_list = repository_interface.get_snapshots(repository_id)
    repository_name = repository_interface.get_repository_name(repository_id)
    return render_template('restore/snapshot_list.html', snapshots=snapshot_list, repository_name=repository_name)


@restore.route(f'/{restore.name}/repositories/snapshot_list/<string:snapshot_id>', methods=['GET', 'POST'])
def snapshot_list(snapshot_id):
    form = RestoreFilesForm()
    if form.validate_on_submit():
        repository = repository_interface.get_repository_from_snap_id(snapshot_id)
        if platform.system() == "Windows":
            if form.destination.data[0] == '/':
                form.destination.data = form.destination.data[1:]
            form.destination.data = form.destination.data.replace('/', os.sep)

        if form.file_data.data == "full_snapshot":
            job_builder = JobBuilder(job_class='restore', job_name='Restore', parameters=dict(
                repository=repository,
                destination_address=form.destination.data,
                snapshot_id=snapshot_id
            ))
        else:
            job_builder = JobBuilder(job_class='restore', job_name='Restore', parameters=dict(
                repository=repository,
                destination_address=form.destination.data,
                object_list=json.loads(form.file_data.data),
                snapshot_id=snapshot_id
            ))
        job_builder.run_job()
        flash("Restore job added to the queue.", category='success')
        return redirect(url_for('restore.repositories'))
    else:
        snapshot_objects = repository_interface.get_snapshot_objects(snapshot_id)
        snapshot = repository_interface.get_snapshot_info(snapshot_id)
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
            
    return render_template('restore/snapshot_restore.html', snapshot_id=snapshot_id, node_list=json.dumps(node_list), form=form)


@restore.route(f'/{restore.name}/repositories/_get_directory_listing')
def get_directory_listing():
    id = request.args.get('id', "none", type=str)
    #id = id.replace("\|\|", " ")
    path = request.args.get('path', 'none', type=str)
    if platform.system() != 'Windows':
        path = '/' + path
    # if id is # then it means we do not really have anything selected
    # and we can return a list of root nodes
    if id == "#":
        root_nodes = []
        if platform.system() == 'Windows':
            for item in filesystem_tools.get_system_drives():
                root_nodes.append({
                    'id': item['device'],
                    'parent': '#',
                    'text': item['device'].replace(os.sep, ""),
                    'children': True})
            return json.dumps(root_nodes)
        elif platform.system() == 'Linux':
            for item in filesystem_tools.get_directory_contents(os.sep):
                root_nodes.append({
                    'id': item['path'].replace(" ", ""),
                    'parent': '#',
                    'text': item['name'],
                    'children': True})
            return json.dumps(root_nodes)
        elif platform.system() == 'Darwin':
            for item in filesystem_tools.get_directory_contents(os.sep):
                root_nodes.append({
                    'id': item['path'].replace(" ", ""),
                    'parent': '#',
                    'text': item['name'],
                    'children': True})
            return json.dumps(root_nodes)
        else:
            return json.dumps({'failure': False, 'errormsg': 'Unsupported operating system to list the files.'}), 500, {'ContentType': 'application/json'}
    else:
        file_nodes = []
        try:
            for item in filesystem_tools.get_directory_contents(path):
                if item['is_dir']:
                    file_nodes.append({
                        'id': item['path'].replace(" ", ""),
                        'text': item['name'],
                        'children': True if item['is_dir'] else False,
                        'icon': 'jstree-folder'})
            return json.dumps(file_nodes)
        except PermissionError as e:
            return json.dumps({'failure': False, 'errormsg': e.strerror}), 500, {'ContentType': 'application/json'}
        except OSError as e:
            return json.dumps({'failure': False, 'errormsg': e.strerror}), 500, {'ContentType': 'application/json'}
        except Exception as e:
            return json.dumps({'failure': False, 'errormsg': e}), 500, {'ContentType': 'application/json'}
