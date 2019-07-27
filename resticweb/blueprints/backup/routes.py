from flask import render_template, Blueprint, request, redirect, url_for, flash
import logging
from resticweb.dictionary.resticweb_constants import BackupSetList, JobStatusFinishedMap
from resticweb.interfaces import backup_sets as backup_sets_interface
from resticweb.models.general import SavedJobs, JobParameter, JobHistory, BackupSet
from resticweb.interfaces.job_history import get_jobs, get_job, delete_jobs
import resticweb.interfaces.saved_backup_jobs as saved_backup_jobs_interface
import resticweb.interfaces.saved_jobs as saved_jobs_interface
import resticweb.interfaces.repository_list as repository_interface
import resticweb.interfaces.backup_sets as backup_sets_interface
from resticweb.tools import filesystem_tools
from resticweb.misc.credential_manager import credential_manager
import traceback
import platform
from .forms import EditBackupJobForm, AddBackupJobForm, get_backup_set_form, get_backup_set_edit_form
import json
from resticweb.tools.job_build import JobBuilder
import humanize
import os

backup = Blueprint('backup', '__name__')
logger = logging.getLogger('mainLogger')


@backup.route(f'/{backup.name}/saved_jobs')
def saved_jobs():
    page = request.args.get('page', 1, type=int)
    items = SavedJobs.query.filter_by(engine_class="backup").order_by(SavedJobs.name.desc()).paginate(page=page, per_page=40)

    return render_template('backup/saved_jobs.html', items=items)


@backup.route(f'/{backup.name}/saved_jobs/_delete', methods=['POST'])
def delete_saved_jobs():
    item_ids = request.get_json().get('item_ids')
    try:
        saved_backup_jobs_interface.delete_jobs(item_ids)
    except Exception as e:
        flash(f"Items not removed: {e}", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@backup.route(f'/{backup.name}/saved_jobs/_get_saved_job_info')
def get_saved_job_info():
    info_dict = {}
    id = request.args.get('id', 0, type=int)
    job = SavedJobs.query.filter_by(id=id).first()
    info_dict['name'] = job.name
    info_dict['notes'] = job.notes
    info_dict['engine_class'] = job.engine_class
    info_dict['time_added'] = job.time_added
    param_backup_set = JobParameter.query.filter_by(job_id=job.id, param_name='backup_set').first()
    backup_set = BackupSet.query.filter_by(id=param_backup_set.param_value).first()
    info_dict['backup_set'] = backup_set.name
    repository = JobParameter.query.filter_by(job_id=job.id, param_name='repository').first()
    repository_name = repository_interface.get_repository_name(repository.param_value)
    info_dict['repository'] = repository_name
    return render_template('sidebar/saved_jobs.html', info_dict=info_dict)


@backup.route(f'/{backup.name}/saved_jobs/_add', methods=['GET', 'POST'])
def add_saved_job():
    engine_class = 'backup'
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    available_backup_sets = backup_sets_interface.get_backup_sets_tuple()
    if len(available_backup_sets) < 1:
        available_backup_sets = [('-1', 'None Available')]
    form = AddBackupJobForm()
    form.repository.choices = available_repositories
    form.backup_set.choices = available_backup_sets
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            engine_class=engine_class)
        param_dict = {}
        credential_dict = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit' and item.id != 'name' and item.id != 'description':
                if item.type == 'UBCredentialField':
                    credential_dict[item.id] = item.data
                else:
                    param_dict[item.id] = item.data
        if len(credential_dict) > 0:
            # credentials_id = credential_manager.add_credentials_from_dict('_'.join(['Job', engine_name, engine_class, form.ub_name.data]), credential_dict)
            credentials_id = credential_manager.add_credentials_from_dict('BackupJob', new_info['name'], credential_dict)
            param_dict['credentials_id'] = credentials_id
        new_info['params'] = param_dict
        saved_backup_jobs_interface.add_job(new_info)
        flash("Job has been saved.", category='success')
        return redirect(url_for('backup.saved_jobs'))
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template(f"backup/saved_jobs_add.html", form=form)

@backup.route(f'/{backup.name}/saved_jobs/_edit/<int:saved_job>', methods=['GET', 'POST'])
def edit_saved_job_backup(saved_job):
    saved_job = SavedJobs.query.filter_by(id=saved_job).first()
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    available_backup_sets = backup_sets_interface.get_backup_sets_tuple()
    if len(available_backup_sets) < 1:
        available_backup_sets = [('-1', 'None Available')]
    form = EditBackupJobForm()
    form.repository.choices = available_repositories
    form.backup_set.choices = available_backup_sets
    form.saved_job_id.data = saved_job.id
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            params=dict(repository=form.repository.data, backup_set=form.backup_set.data),
            saved_job_id=form.saved_job_id.data
        )
        saved_jobs_interface.update_job(new_info)
        flash("Backup job successfully edited.", category='success')
        return redirect(url_for('backup.saved_jobs'))
    else:
        for param in saved_job.parameters:
            if param.param_name == "repository":
                form.repository.default = param.param_value
            if param.param_name == 'backup_set':
                form.backup_set.default = param.param_value
        form.process()
        form.description.data = saved_job.notes
        form.name.data = saved_job.name
        form.saved_job_id.data = saved_job.id
    return render_template("backup/saved_jobs_add.html", form=form)

@backup.route(f'/{backup.name}/saved_jobs/_run_jobs', methods=['GET', 'POST'])
def run_saved_jobs():
    item_ids = request.get_json().get('item_ids')
    for item_id in item_ids:
        # saved_jobs_interface.run_saved_job_backup(item_id)
        job_builder = JobBuilder(saved_job_id=item_id)
        job_builder.run_job()
    flash("Job/s added to queue", category='success')
    return redirect(url_for('backup.saved_jobs'))


@backup.route(f'/{backup.name}/backup_sets')
def backup_sets():
    page = request.args.get('page', 1, type=int)
    items = BackupSet.query.order_by(BackupSet.time_added.desc()).paginate(page=page, per_page=40)
    for item in items.items:
        item.type = BackupSetList.BACKUP_SETS[item.type]
    return render_template('backup/backup_sets.html', items=items)


@backup.route(f'/{backup.name}/backup_sets/_add/<int:backup_set>', methods=['GET', 'POST'])
def add_backup_set(backup_set):
    form = get_backup_set_form(backup_set)
    if form.validate_on_submit():
        new_info = {}
        new_info['type'] = backup_set
        new_info['name'] = form.name.data
        new_info['source'] = platform.node()
        new_info['backup_object_data'] = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit' and item.id != 'name':
                new_info['backup_object_data'][item.id] = item.data
        try:
            backup_sets_interface.add_backup_set(new_info)
            flash(f"Added backup set {new_info['name']} successfully.", category='success')
        except Exception as e:
            flash(f"Failed to add backup set. {e}", category='error')
            logger.error("Failed to add backup set.")
            logger.error(traceback.format_exc())
        return redirect(url_for('backup.backup_sets'))
    return render_template(f"backup/backup_sets_add_{backup_set}.html", form=form)

@backup.route(f'/{backup.name}/backup_sets/_edit/<int:backup_set>', methods=['GET', 'POST'])
def edit_backup_set(backup_set):
    current_info, current_object_list = backup_sets_interface.get_backup_set_info(backup_set)
    for item in current_object_list:
        item = item.replace(' ', '')
    form = get_backup_set_edit_form(current_info['type'])
    excluded_items = []
    for item in backup_sets_interface.get_backup_set_objects(backup_set):
        if item[0] == '-':
            excluded_items.append(dict(
                path=item[1:],
                id=item[1:].replace(' ', '')
            ))
    form.backup_set_id.data = backup_set
    if form.validate_on_submit():
        new_data = {}
        new_data['id'] = backup_set
        new_data['name'] = form.name.data
        new_data['source'] = form.source.data
        new_data['backup_object_data'] = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit' and item.id != 'name':
                new_data['backup_object_data'][item.id] = item.data
        try:
            backup_sets_interface.update_backup_set(new_data)
            flash(f"Edited backup set {new_data['name']}", category='success')
        except Exception as e:
            flash(f"Failed to edit backup set. {e}", category='error')
            logger.error("Failed to edit backup set.")
            logger.error(traceback.format_exc())
        return redirect(url_for('backup.backup_sets'))

    elif request.method == 'GET':
        form.name.data = current_info.get('name')
        form.source.data = current_info.get('source')
        if current_info.get('source') != platform.node():
            current_object_list = -1
            current_info['data'] = -1
    return render_template(f"backup/backup_sets_edit_{current_info.get('type')}.html", form=form, current_object_list=current_object_list, backup_set_data=current_info['data'], excluded_items=excluded_items)


@backup.route(f'/{backup.name}/backup_sets/_add', methods=['GET', 'POST'])
def get_backup_set():
    if request.method == 'POST':
        backup_set = request.form['backup-set-select']
        return redirect(url_for('backup.add_backup_set', backup_set=backup_set))
    available_backup_sets = []
    for key, value in BackupSetList.BACKUP_SETS.items():
        available_backup_sets.append((key, value))
    return render_template("backup/backup_sets_add.html", available_backup_sets=available_backup_sets)


@backup.route(f'/{backup.name}/backup_sets/_delete', methods=['GET', 'POST'])
def delete_backup_set():
    item_ids = request.get_json().get('item_ids')
    try:
        backup_sets_interface.delete_backup_sets(item_ids)
    except Exception as e:
        flash(f"Items not removed: {e}", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@backup.route(f'/{backup.name}/backup_sets/_get_backup_set_info')
def get_backup_set_info():
    info_dict = {}
    id = request.args.get('id', 0, type=int)
    # info_dict['name'] = get_loc_info(location_id)['name']
    info_dict, set_items = backup_sets_interface.get_backup_set_info(id)
    return render_template('sidebar/backup_sets.html', info_dict=info_dict, set_items=set_items)


@backup.route(f'/{backup.name}/backup_sets/_get_directory_listing')
def get_directory_listing():
    id = request.args.get('id', "none", type=str)
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
                file_nodes.append({
                    'id': item['path'].replace(" ", ""),
                    'text': item['name'],
                    'children': True if item['is_dir'] else False,
                    'icon': 'jstree-folder' if item['is_dir'] else 'jstree-file'})
            return json.dumps(file_nodes)
        except PermissionError as e:
            return json.dumps({'failure': False, 'errormsg': e.strerror}), 500, {'ContentType': 'application/json'}
        except OSError as e:
            return json.dumps({'failure': False, 'errormsg': e.strerror}), 500, {'ContentType': 'application/json'}
        except Exception as e:
            return json.dumps({'failure': False, 'errormsg': e}), 500, {'ContentType': 'application/json'}

@backup.route(f'/{backup.name}/job_history')
def job_history():
    page = request.args.get('page', 1, type=int)
    items = JobHistory.query.filter_by(type='Backup').order_by(JobHistory.time_finished.desc()).paginate(page=page, per_page=40)
    for item in items.items:
        item.status = JobStatusFinishedMap.JOB_STATUS_FINISHED[item.status]
    return render_template('backup/job_history.html', items=items)


@backup.route(f'/{backup.name}/job_history/_get_history_info')
def get_history_info():
    id = request.args.get('id', 0, type=int)
    info_dict = get_job(id)
    if info_dict.log:
        try:
            info_dict.log = json.loads(info_dict.log)
        except json.decoder.JSONDecodeError:
            # if the log is not a list, we just add the whole string
            # to a list so that it's displayed properly
            info_dict.log = [info_dict.log]
    if info_dict.result:
        try:
            info_dict.result = json.loads(info_dict.result)
            if info_dict.result:
                try:
                    info_dict.result['data_added'] = humanize.naturalsize(info_dict.result.get('data_added'), binary=True)
                    info_dict.result['total_bytes_processed'] = humanize.naturalsize(info_dict.result.get('total_bytes_processed'), binary=True)
                except Exception:
                    pass
        except json.decoder.JSONDecodeError:
            pass
    return render_template('sidebar/job_history_backup.html', info_dict=info_dict)


@backup.route(f'/{backup.name}/job_history/_delete', methods=['POST'])
def delete_job_history():
    job_list = request.get_json().get('item_ids')
    try:
        delete_jobs(job_list)
    except Exception as e:
        flash(f"Items not removed: {e}", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}