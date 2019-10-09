from flask import Blueprint, render_template, request, flash, Response, redirect, url_for
from resticweb.interfaces.job_history import get_jobs, get_job, delete_jobs
# from resticweb.interfaces.saved_jobs import delete_jobs as delete_jobs_s, add_job
import resticweb.interfaces.saved_jobs as saved_jobs_interface
import resticweb.interfaces.backup_sets as backup_sets_interface
import resticweb.interfaces.repository_list as repository_interface
from resticweb import db
from resticweb.misc import job_queue as global_job_queue
from resticweb.tools.job_build import JobBuilder
from resticweb.engine_classes.class_name_map import get_available_classes, get_class_from_name
from resticweb.dictionary.resticweb_constants import JobStatusFinishedMap, \
    JobStatusMap, ScheduleConstants
from resticweb.models.general import JobHistory, SavedJobs, Repository, Schedule, ScheduleJobMap
import json
from .forms import AddCheckJobForm, EditCheckJobForm, AddPruneJobForm, EditPruneJobForm, AddScheduleForm, EditScheduleForm, \
    AddForgetJobForm, EditForgetJobForm
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

'''
@jobs.route(f'/{jobs.name}/job_queue/_stop', methods=['POST'])
def stop_jobs():
    job_ids = request.get_json().get('item_ids')
    for job_id in job_ids:
        process_manager.kill_process(job_id)
    flash("Selected processes have been terminated.", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
'''

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
    if history_info.result == 'null':
        history_info.result = None
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
    if job.engine_class == 'check' or job.engine_class == 'prune':
        info_dict = {}
        info_dict['name'] = job.name
        info_dict['notes'] = job.notes
        for param in job.parameters:
            if param.param_name == 'repository':
                repository = Repository.query.filter_by(id=param.param_value).first()
            if param.param_name == 'additional_params':
                info_dict['additional_params'] = param.param_value
        if repository:
            info_dict['repository'] = repository.name
        else:
            info_dict['repository'] = "undefined"
        return render_template(f'sidebar/saved_jobs_{job.engine_class}.html', info_dict=info_dict)
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
        return redirect(url_for('backup.edit_saved_job_backup', saved_job=saved_job))
    elif engine_class == 'check':
        return edit_saved_job_check(editable_job)
    elif engine_class == 'prune':
        return edit_saved_job_prune(editable_job)
    elif engine_class == 'forget_policy':
        return edit_saved_job_forget(editable_job)
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
    elif engine_class == 'forget_policy':
        return add_saved_job_forget()


def add_saved_job_forget():
    engine_class = 'forget_policy'
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    available_backup_sets = backup_sets_interface.get_backup_sets_tuple()
    if len(available_backup_sets) < 1:
        available_backup_sets = [('-1', 'None Available')]
    form = AddForgetJobForm()
    form.repository.choices = available_repositories
    form.backup_set.choices = available_backup_sets
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            engine_class=engine_class)
        param_dict = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit' and item.id != 'name' and item.id != 'description':
                param_dict[item.id] = item.data
        new_info['params'] = param_dict
        saved_jobs_interface.add_job(new_info)
        flash("Job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    # we can use the same template as it's just going to be the same fields
    # as the fields in the edit form
    return render_template(f"jobs/saved_jobs_add_forget.html", form=form)


def edit_saved_job_forget(saved_job):
    available_repositories = repository_interface.get_engine_repositories()
    if len(available_repositories) < 1:
        available_repositories = [('-1', 'None Available')]
    available_backup_sets = backup_sets_interface.get_backup_sets_tuple()
    if len(available_backup_sets) < 1:
        available_backup_sets = [('-1', 'None Available')]
    form = EditForgetJobForm()
    form.repository.choices = available_repositories
    form.backup_set.choices = available_backup_sets
    form.saved_job_id.data = saved_job.id
    if form.validate_on_submit():
        new_info = dict(
            name=form.name.data,
            notes=form.description.data,
            #params=dict(repository=form.repository.data, backup_set=form.backup_set.data),
            saved_job_id=form.saved_job_id.data
        )
        param_dict = {}
        for item in form:
            if item.id != 'csrf_token' and item.id != 'submit' and item.id != 'name' and item.id != 'description':
                param_dict[item.id] = item.data
        new_info['params'] = param_dict
        saved_jobs_interface.update_job(new_info)
        flash("Forget job successfully edited.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    else:
        for param in saved_job.parameters:
            if param.param_name == "repository":
                form.repository.default = param.param_value
            if param.param_name == 'backup_set':
                form.backup_set.default = param.param_value
        form.process()
        for param in saved_job.parameters:
            if param.param_name == 'additional_params':
                form.additional_params.data = param.param_value
            if param.param_name == 'keep_last':
                form.keep_last.data = param.param_value
            if param.param_name == 'keep_hourly':
                form.keep_hourly.data = param.param_value
            if param.param_name == 'keep_daily':
                form.keep_daily.data = param.param_value
            if param.param_name == 'keep_weekly':
                form.keep_weekly.data = param.param_value
            if param.param_name == 'keep_monthly':
                form.keep_monthly.data = param.param_value
            if param.param_name == 'keep_yearly':
                form.keep_yearly.data = param.param_value
            if param.param_name == 'keep_within':
                form.keep_within.data = param.param_value
            if param.param_name == 'prune':
                if int(param.param_value) > 0:
                    form.prune.data = True
                else:
                    form.prune.data = False
        form.description.data = saved_job.notes
        form.name.data = saved_job.name
        form.saved_job_id.data = saved_job.id
    return render_template("jobs/saved_jobs_add_forget.html", form=form)


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
            params=dict(repository=form.repository.data, additional_params=form.additional_params.data)
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
            params=dict(repository=form.repository.data, additional_params=form.additional_params.data),
            saved_job_id=form.saved_job_id.data,
        )
        saved_jobs_interface.update_job(new_info)
        flash("Check job has been saved.", category='success')
        return redirect(url_for('jobs.saved_jobs'))
    else:
        for param in saved_job.parameters:
            if param.param_name == "repository":
                form.repository.default = param.param_value
                form.process()
        for param in saved_job.parameters:
            if param.param_name == 'additional_params':
                form.additional_params.data = param.param_value
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
            params=dict(repository=form.repository.data, additional_params=form.additional_params.data)
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
            params=dict(repository=form.repository.data, additional_params=form.additional_params.data),
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
        for param in saved_job.parameters:
            if param.param_name == 'additional_params':
                form.additional_params.data = param.param_value
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
    for item in items.items:
        item.policy = get_schedule_policy(item.id)
    return render_template('jobs/schedules.html', items=items)


@jobs.route(f'/{jobs.name}/schedules/_add', methods=['GET', 'POST'])
def schedules_add():
    form = AddScheduleForm()
    scheduled_days = []
    if form.monday.data:
        scheduled_days.append('monday')
    if form.tuesday.data:
        scheduled_days.append('tuesday')
    if form.wednesday.data:
        scheduled_days.append('wednesday')
    if form.thursday.data:
        scheduled_days.append('thursday')
    if form.friday.data:
        scheduled_days.append('friday')
    if form.saturday.data:
        scheduled_days.append('saturday')
    if form.sunday.data:
        scheduled_days.append('sunday')
    available_time_units = [(unit, unit) for unit in ScheduleConstants.TIME_UNITS]
    form.time_unit.choices = available_time_units
    if form.validate_on_submit():
        try:
            job_scheduler.add_schedule(form.name.data,
                form.time_unit.data,
                form.description.data,
                form.time_interval.data,
                form.time_at.data,
                form.missed_timeout.data,
                json.loads(form.job_list.data), # list of tuples (job_id, sort)
                scheduled_days) 
            flash("Schedule has been saved.", category='success')
        except Exception as e:
            flash(f"Failed to add schedule: {e}", category='error')
        return redirect(url_for('jobs.schedules'))
    return render_template('jobs/schedules_add.html', form=form)

@jobs.route(f'/{jobs.name}/schedules/_edit/<int:schedule_id>', methods=['GET', 'POST'])
def schedules_edit(schedule_id):
    form = EditScheduleForm()
    available_time_units = [(unit, unit) for unit in ScheduleConstants.TIME_UNITS]
    form.time_unit.choices = available_time_units
    form.schedule_id.data = schedule_id
    if form.validate_on_submit():
        scheduled_days = []
        if form.monday.data:
            scheduled_days.append('monday')
        if form.tuesday.data:
            scheduled_days.append('tuesday')
        if form.wednesday.data:
            scheduled_days.append('wednesday')
        if form.thursday.data:
            scheduled_days.append('thursday')
        if form.friday.data:
            scheduled_days.append('friday')
        if form.saturday.data:
            scheduled_days.append('saturday')
        if form.sunday.data:
            scheduled_days.append('sunday')
        job_scheduler.update_schedule(
            form.name.data,
            form.time_unit.data,
            schedule_id,
            form.description.data,
            form.time_interval.data,
            form.time_at.data,
            form.missed_timeout.data,
            scheduled_days
        )
        if form.jobs_changed.data:
            job_scheduler.update_jobs(schedule_id, json.loads(form.job_list.data))
        flash(f"Edited schedule {form.name.data}", category='success')
        return redirect(url_for('jobs.schedules'))
    else:
        schedule = Schedule.query.filter_by(id=schedule_id).first()
        form.name.data = schedule.name
        form.time_unit.data = schedule.time_unit
        form.description.data = schedule.description
        form.time_interval.data = schedule.time_interval
        form.time_at.data = schedule.time_at
        form.missed_timeout.data = schedule.missed_timeout
        previous_days = json.loads(schedule.days)
        for day in previous_days:
            if day == 'monday':
                form.monday.data = True
            elif day == 'tuesday':
                form.tuesday.data = True
            elif day == 'wednesday':
                form.wednesday.data = True
            elif day == 'thursday':
                form.thursday.data = True
            elif day == 'friday':
                form.friday.data = True
            elif day == 'saturday':
                form.saturday.data = True
            elif day == 'sunday':
                form.sunday.data = True
        scheduled_jobs = []
        job_maps = ScheduleJobMap.query.filter_by(schedule_id=schedule_id).order_by(ScheduleJobMap.sort.asc()).all()
        for job_map in job_maps:
            scheduled_jobs.append(
                dict(
                    id=job_map.job_id,
                    name=job_map.saved_job.name
                )
            )
    return render_template(f'jobs/schedules_edit.html', form=form, table_items=scheduled_jobs)


@jobs.route(f'/{jobs.name}/schedules/_delete', methods=['POST'])
def delete_schedules():
    item_ids = request.get_json().get('item_ids')
    try:
        for id in item_ids:
            job_scheduler.delete_schedule(id)
    except Exception as e:
        flash(f"Items not removed {e}", category='error')
        return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@jobs.route(f'/{jobs.name}/schedules/_job_select', methods=['GET'])
def job_select():
    page = request.args.get('page', 1, type=int)
    items = SavedJobs.query.order_by(SavedJobs.name.desc()).paginate(page=page, per_page=40)
    return render_template('jobs/schedules_job_select.html', items=items)


@jobs.route(f'/{jobs.name}/schedules/_toggle_schedule_pause', methods=['POST'])
def toggle_schedule_pause():
    item_id = request.get_json().get('item_id')
    # schedule = Schedule.query.filter_by(id=item_id).first()
    try:
        job_scheduler.toggle_pause(item_id)
        schedule = Schedule.query.filter_by(id=item_id).first()
        return json.dumps({'success': True, 'item_values': {'next_run': f'{schedule.next_run}', 'paused': schedule.paused}}), 200, {'ContentType': 'application/json'}
    except Exception as e:
        return json.dumps({'success': False, 'errormsg': repr(e)}), 500, {'ContentType': 'application/json'}


@jobs.route(f'/{jobs.name}/schedules/_get_schedule_info')
def get_schedule_info():
    id = request.args.get('id', 0, type=int)
    schedule = Schedule.query.filter_by(id=id).first()
    info_dict = {}
    info_dict['name'] = schedule.name
    info_dict['description'] = schedule.description
    info_dict['next_run'] = schedule.next_run
    info_dict['policy'] = get_schedule_policy(id)
    info_dict['missed_timeout'] = schedule.missed_timeout
    if schedule.paused:
        info_dict['paused'] = True
    else:
        info_dict['paused'] = False
    info_dict['jobs'] = []
    for job_map in schedule.schedule_job_maps:
        info_dict['jobs'].append(job_map.saved_job.name)
    return render_template("sidebar/schedule.html", info_dict=info_dict)
    


def get_schedule_policy(schedule_id):
    schedule = Schedule.query.filter_by(id=schedule_id).first()
    ret = []
    ret.append('Every')
    if schedule.time_interval:
        ret.append(schedule.time_interval)
    ret.append(schedule.time_unit)
    if schedule.time_at:
        ret.append(f'at {schedule.time_at}')
    days = json.loads(schedule.days)
    if len(days) > 0:
        ret.append("on")
        ret.append(", ".join(days))
    return " ".join(str(ret_val) for ret_val in ret)