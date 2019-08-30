from flask import Blueprint, render_template, request, flash, Response, redirect, url_for
from resticweb.interfaces.job_history import get_jobs, get_job, delete_jobs
# from resticweb.interfaces.saved_jobs import delete_jobs as delete_jobs_s, add_job
import resticweb.interfaces.saved_jobs as saved_jobs_interface
from resticweb import db
from resticweb.misc import job_queue as global_job_queue
from resticweb.tools.job_build import JobBuilder
from resticweb.engine_classes.class_name_map import get_available_classes, get_class_from_name
from resticweb.dictionary.resticweb_constants import JobStatusFinishedMap, \
    JobStatusMap
import resticweb.interfaces.repository_list as repository_interface
from resticweb.models.general import JobHistory, SavedJobs, Repository, Schedule, ScheduleJobMap
import json
from .forms import AddCheckJobForm, EditCheckJobForm, AddPruneJobForm, EditPruneJobForm, AddScheduleForm
from time import sleep
from resticweb.misc.job_scheduler import job_scheduler

jobs = Blueprint('jobs', '__name__')


@jobs.route(f'/{jobs.name}/')
@jobs.route(f'/{jobs.name}/job_queue')
def job_queue():
    items = global_job_queue.get_job_queue_info()
    for item in items:
        item['status'] = JobStatusMap.JOB_STATUS[item['status']]
    return render_template('jobs/job_queue.html', items=items)


@jobs.route(f'/{jobs.name}/job_queue/_update')
def update_job_queue():
    def update_stream():
        while True:
            job_list = global_job_queue.get_job_queue_info()
            for item in job_list:
                # this will change the status from an internal status value into
                # a human readable status value. Essentially an enum
                item['status'] = JobStatusMap.JOB_STATUS[item['status']]
                # yield 'data: {' + f'"id": "{item["id"]}", "name": "status", "data": "{global_job_queue.get_job_info(item["id"], 'status')}"' + '}\n\n'
            yield f'data: {json.dumps(job_list)}\n\n'
            sleep(1)
    return Response(update_stream(), mimetype="text/event-stream")


@jobs.route(f'/{jobs.name}/job_queue/_stop', methods=['POST'])
def stop_jobs():
    job_ids = request.get_json().get('item_ids')
    for job_id in job_ids:
        process_manager.kill_process(job_id)
    flash("Selected processes have been terminated.", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@jobs.route(f'/{jobs.name}/job_queue/_update_job_info/<int:job_id>')
def update_job_info(job_id):
    def update_stream():
        while True:
            job_type = global_job_queue.get_job_info(job_id, 'type')
            if job_type == 'Backup':
                requested_data_list = ['total_files', 'files_done', 'total_bytes', 'bytes_done', 'current_files', 'seconds_elapsed', 'seconds_remaining']
                return_dict = global_job_queue.get_job_process_info(job_id, requested_data_list)
                return_dict['id'] = job_id
            yield f'data: {json.dumps(return_dict)}\n\n'
            sleep(1)
    return Response(update_stream(), mimetype="text/event-stream")


@jobs.route(f'/{jobs.name}/job_queue/_get_job_status')
def get_job_status():
    job_id = request.args.get('id', 0, type=int)
    status = global_job_queue.get_job_info(job_id, 'status')
    if not status:
        return json.dumps({'data': 'deleted', 'name': 'status', 'id': job_id})
    status = JobStatusMap.JOB_STATUS[status]
    return json.dumps({'data': status, 'name': 'status', 'id': job_id})


@jobs.route(f'/{jobs.name}/job_queue/_get_job_info')
def get_job_info():
    job_id = request.args.get('id', 0, type=int)
    job_type = global_job_queue.get_job_info(job_id, 'type')
    if job_type == 'Backup':
        requested_data_list = ['total_files', 'files_done', 'total_bytes', 'bytes_done', 'current_files', 'seconds_elapsed', 'seconds_remaining']
        return_dict = global_job_queue.get_job_process_info(job_id, requested_data_list)
        return_dict['id'] = job_id
        return render_template(f'sidebar/job_queue_backup.html', info_dict=return_dict)
    else:
        return ""


@jobs.route(f'/{jobs.name}/job_history')
def job_history():
    page = request.args.get('page', 1, type=int)
    items = JobHistory.query.order_by(JobHistory.time_finished.desc()).paginate(page=page, per_page=40)
    for item in items.items:
        item.status = JobStatusFinishedMap.JOB_STATUS_FINISHED[item.status]
    return render_template('jobs/job_history.html', items=items, paginate=True)


@jobs.route(f'/{jobs.name}/job_history/_get_history_info')
def get_history_info():
    id = request.args.get('id', 0, type=int)
    history_info = JobHistory.query.filter_by(id=id).first()
    if history_info.type == 'Backup':
        from resticweb.blueprints.backup.routes import get_history_info as get_backup_history_info
        return get_backup_history_info()
    if history_info.log:
        try:
            history_info.log = json.loads(history_info.log)
        except json.decoder.JSONDecodeError:
            # if the log is not a list, we just add the whole string
            # to a list so that it's displayed properly
            history_info.log = [history_info.log]
    '''
    history_info = dict(
        name=history_info.name,
        status=history_info.status,
        type=history_info.type,
        log=history_info.log,
        time_started=history_info.time_started,
        time_finished=history_info.time_finished,
        time_elapsed=history_info.time_elapsed,
        time_added = 
    )
    '''
    return render_template('sidebar/job_history.html', info_dict=history_info)


@jobs.route(f'/{jobs.name}/job_history/_delete', methods=['POST'])
def delete_job_history():
    job_list = request.get_json().get('item_ids')
    try:
        delete_jobs(job_list)
    except Exception as e:
        flash("Items not removed", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@jobs.route(f'/{jobs.name}/saved_jobs')
def saved_jobs():
    page = request.args.get('page', 1, type=int)
    items = SavedJobs.query.order_by(SavedJobs.name.desc()).paginate(page=page, per_page=40)

    return render_template('jobs/saved_jobs.html', items=items)


@jobs.route(f'/{jobs.name}/saved_jobs/_delete', methods=['POST'])
def delete_saved_jobs():
    item_ids = request.get_json().get('item_ids')
    try:
        saved_jobs_interface.delete_jobs(item_ids)
    except Exception as e:
        flash(f"Items not removed {e}", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@jobs.route(f'/{jobs.name}/saved_jobs/_get_saved_job_info')
def get_saved_job_info():
    id = request.args.get('id', 0, type=int)
    job = SavedJobs.query.filter_by(id=id).first()
    if job.engine_class == 'check':
        info_dict = {}
        info_dict['name'] = job.name
        info_dict['notes'] = job.notes
        for param in job.parameters:
            if param.param_name == 'repository':
                repository = Repository.query.filter_by(id=param.param_value).first()
        if repository:
            info_dict['repository'] = repository.name
        else:
            info_dict['repository'] = "undefined"
        return render_template('sidebar/saved_jobs_check.html', info_dict=info_dict)
    elif job.engine_class == 'prune':
        info_dict = {}
        info_dict['name'] = job.name
        info_dict['notes'] = job.notes
        for param in job.parameters:
            if param.param_name == 'repository':
                repository = Repository.query.filter_by(id=param.param_value).first()
        if repository:
            info_dict['repository'] = repository.name
        else:
            info_dict['repository'] = "undefined"
        return render_template('sidebar/saved_jobs_prune.html', info_dict=info_dict)
    elif job.engine_class == 'backup':
        from resticweb.blueprints.backup.routes import get_saved_job_info as get_backup_job_info
        return get_backup_job_info()
    else:
        return ""


@jobs.route(f'/{jobs.name}/saved_jobs/_add', methods=['GET', 'POST'])
def submit_engine_data():

    if request.method == 'POST':
        engine_class = request.form.get('job-class-select')
        if engine_class is None:
            return redirect(url_for('jobs.saved_jobs'))
        else:
            return redirect(url_for('jobs.add_saved_job', engine_class=engine_class))

    engine_classes = get_available_classes()
    return render_template('jobs/saved_jobs_add.html', available_engine_classes=engine_classes)


@jobs.route(f'/{jobs.name}/saved_jobs/_edit/<int:saved_job>', methods=['GET', 'POST'])
#@jobs.route(f'/{jobs.name}/saved_jobs/_add?engine=<string:engine_name>', methods=['GET', 'POST'])
def edit_saved_job(saved_job):
    editable_job = SavedJobs.query.filter_by(id=saved_job).first()
    engine_class = editable_job.engine_class
    if engine_class == 'backup':
        return redirect(url_for('backup.add_saved_job'))
    elif engine_class == 'check':
        return edit_saved_job_check(editable_job)
    elif engine_class == 'prune':
        return edit_saved_job_prune(editable_job)
    else:
        return ""


@jobs.route(f'/{jobs.name}/saved_jobs/_add/<string:engine_class>', methods=['GET', 'POST'])
#@jobs.route(f'/{jobs.name}/saved_jobs/_add?engine=<string:engine_name>', methods=['GET', 'POST'])
def add_saved_job(engine_class):

    if engine_class == 'backup':
        return redirect(url_for('backup.add_saved_job'))
    elif engine_class == 'repository':
        return redirect(url_for('repositories.choose_repository_type'))
    elif engine_class == 'restore':
        return redirect(url_for('restore.repositories'))
    elif engine_class == 'check':
        return add_saved_job_check()
    elif engine_class == 'prune':
        return add_saved_job_prune()


def add_saved_job_check():
    engine_class = 'check'
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    form = AddCheckJobForm()
    form.repository.choices = available_repositories
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            engine_class=engine_class,
            params=dict(repository=form.repository.data)
        )
        saved_jobs_interface.add_job(new_info)
        flash("Check job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    return render_template("jobs/saved_jobs_add_check.html", form=form)

def edit_saved_job_check(saved_job):
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    form = EditCheckJobForm()
    form.repository.choices = available_repositories
    form.saved_job_id.data = saved_job.id
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            params=dict(repository=form.repository.data),
            saved_job_id=form.saved_job_id.data
        )
        saved_jobs_interface.update_job(new_info)
        flash("Check job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    else:
        for param in saved_job.parameters:
            if param.param_name == "repository":
                form.repository.default = param.param_value
                form.process()
        form.description.data = saved_job.notes
        form.name.data = saved_job.name
        form.saved_job_id.data = saved_job.id
    return render_template("jobs/saved_jobs_add_check.html", form=form)

def add_saved_job_prune():
    engine_class = 'prune'
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    form = AddPruneJobForm()
    form.repository.choices = available_repositories
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            engine_class=engine_class,
            params=dict(repository=form.repository.data)
        )
        saved_jobs_interface.add_job(new_info)
        flash("Prune job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    return render_template("jobs/saved_jobs_add_prune.html", form=form)

def edit_saved_job_prune(saved_job):
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    form = EditPruneJobForm()
    form.repository.choices = available_repositories
    form.saved_job_id.data = saved_job.id
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            params=dict(repository=form.repository.data),
            saved_job_id=form.saved_job_id.data
        )
        saved_jobs_interface.update_job(new_info)
        flash("Prune job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    else:
        for param in saved_job.parameters:
            if param.param_name == "repository":
                form.repository.default = param.param_value
                form.process()
        form.description.data = saved_job.notes
        form.name.data = saved_job.name
        form.saved_job_id.data = saved_job.id
    return render_template("jobs/saved_jobs_add_prune.html", form=form)



    '''
    if form.validate_on_submit():
        new_info = {}
        new_info['ub_name'] = form.name.data
        new_info['ub_description'] = form.description.data
        saved_jobs_interface.add_job(new_info)
        flash("Job has been added", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template("jobs/saved_jobs_add.html", form=form)
    '''


@jobs.route(f'/{jobs.name}/saved_jobs/_run_jobs', methods=['GET', 'POST'])
def run_saved_jobs():
    item_ids = request.get_json().get('item_ids')
    for item_id in item_ids:
        job_builder = JobBuilder(saved_job_id=item_id)
        job_builder.run_job()
    flash("Job added to queue", category='success')
    return redirect(url_for('jobs.saved_jobs'))

'''
@jobs.route(f'/{jobs.name}/saved_jobs/_get_engine_classes')
def get_engine_classes():
    engine_name = request.args.get('engine_name', "none", type=str)
    classes = plugin_tools.get_engine_classes(engine_name)
    return json.dumps(classes)
'''

'''
@system.route(f'/{system.name}/processes/_update_queue')
def update_queue():
    def update_stream():
        while True:
            job_list = global_job_queue.get_job_queue_info()
            yield f'data: {json.dumps(job_list)}\n\n'
            sleep(10)
    return Response(update_stream(), mimetype="text/event-stream")
'''


@jobs.route(f'/{jobs.name}/schedules')
def schedules():
    page = request.args.get('page', 1, type=int)
    items = Schedule.query.order_by(Schedule.name.desc()).paginate(page=page, per_page=40)

    return render_template('jobs/schedules.html', items=items)


@jobs.route(f'/{jobs.name}/schedules/_add', methods=['GET', 'POST'])
def schedules_add():
    form = AddScheduleForm()

    available_time_units = [
        ('minute', 'minute'),
        ('minutes', 'minutes'),
        ('hour', 'hour'),
        ('hours', 'hours'),
        ('day', 'day'),
        ('days', 'days'),
        ('week', 'week'),
        ('weeks', 'weeks'),
        ('monday', 'monday'),
        ('tuesday', 'tuesday'),
        ('wednesday', 'wednesday'),
        ('thursday', 'thursday'),
        ('friday', 'friday'),
        ('saturday', 'saturday'),
        ('sunday', 'sunday'),
    ]

    form.time_unit.choices = available_time_units
    return render_template('jobs/schedules_add.html', form=form)