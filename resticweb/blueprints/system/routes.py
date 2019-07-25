from flask import Blueprint, render_template, flash, redirect, \
    url_for, request, Response
from flask_login import login_required, current_user
from .forms import UpdateAccountForm, UnlockCredentialStoreForm, \
    EditCredentialsForm, DecryptCredentialStoreForm, EncryptCredentialStoreForm
from resticweb import bcrypt, db, process_manager
from resticweb.misc.credential_manager import credential_manager
from resticweb.models.general import CredentialGroup
# from resticweb.tools.credential_tools import credentials_locked, \
#    get_all_credential_groups, get_group_credentials, remove_credentials, \
#    set_crypt_key
import logging
import json
import traceback
from time import sleep

system = Blueprint('system', '__name__')
logger = logging.getLogger('debugLogger')


@system.route(f'/{system.name}', methods=['GET', 'POST'])
@system.route(f'/{system.name}/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        current_user.username = form.username.data
        if form.password.data != "":
            hashed_password = bcrypt.generate_password_hash(
                form.password.data).decode('utf-8')
            current_user.password = hashed_password
        db.session.commit()
        flash("Account information has been updated", category='success')
        return redirect(url_for('system.account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
    return render_template('system/account.html', form=form)


@system.route(f'/{system.name}/system')
def settings():
    return render_template('system/settings.html')


@system.route(f'/{system.name}/plugins')
def plugins():
    return render_template('system/plugins.html')


@system.route(f'/{system.name}/processes')
def processes():
    process_list = process_manager.get_process_list()
    return render_template('system/processes.html', items=process_list)


@system.route(f'/{system.name}/processes/_get_process_info')
def get_process_info():
    info_dict = {}
    process_id = request.args.get('id', 0, type=int)
    info_dict['description'] = process_manager.get_description(process_id)
    return render_template('sidebar/processes.html', info_dict=info_dict)


@system.route(f'/{system.name}/processes/_get_process_status')
def get_process_status():
    process_id = request.args.get('id', 0, type=int)
    status = process_manager.get_info(process_id, 'status')
    if status:
        return json.dumps({'name': 'status', 'id': process_id, 'data': status})
    else:
        return json.dumps({'name': 'status', 'id': process_id, 'data': 'deleted'})


@system.route(f'/{system.name}/processes/_update_processes')
def update_processes():
    def update_stream():
        while True:
            process_list = process_manager.get_process_list()
            yield f'data: {json.dumps(process_list)}\n\n'
            sleep(5)
    return Response(update_stream(), mimetype="text/event-stream")


@system.route(f'/{system.name}/processes/_terminate', methods=['POST'])
def kill_processes():
    process_list_ids = request.get_json().get('item_ids')
    for process_id in process_list_ids:
        process_manager.kill_process(process_id)
    flash("Selected processes have been terminated.", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@system.route(f'/{system.name}/credentials', methods=['GET', 'POST'])
def credentials():
    locked = credential_manager.credentials_locked()
    encrypted = credential_manager.credentials_encrypted()
    credential_groups = credential_manager.get_all_credential_groups()
    return render_template(
        'system/credentials.html',
        credential_database_locked=locked,
        credential_database_encrypted=encrypted,
        credential_groups=credential_groups)


@system.route(f'/{system.name}/credentials/_encrypt_credentials', methods=['GET', 'POST'])
def encrypt_credentials():
    form = EncryptCredentialStoreForm()
    if form.validate_on_submit():
        try:
            credential_manager.encrypt_credentials(form.password.data)
        except Exception:
            flash("Failed to encrypt credentials", category='error')
            logger.error(traceback.format_exc())
        return redirect(url_for('system.credentials'))
    return render_template(
        'system/credentials_encrypt.html',
        form=form
    )


@system.route(f'/{system.name}/credentials/_decrypt_credentials', methods=['GET', 'POST'])
def decrypt_credentials():
    form = DecryptCredentialStoreForm()
    if form.validate_on_submit():
        try:
            credential_manager.decrypt_credentials()
        except Exception as e:
            flash("Failed to decrypt credentials", category='error')
            logger.error(e)
        return redirect(url_for('system.credentials'))
    return render_template(
        'system/credentials_decrypt.html',
        form=form
    )


@system.route(f'/{system.name}/credentials/_unlock_credentials', methods=['GET', 'POST'])
def unlock_credentials():
    form = UnlockCredentialStoreForm()
    if form.validate_on_submit():
        try:
            credential_manager.unlock_credentials(form.password.data)
        except Exception:
            flash("Failed to unlock credentials", category='error')
            logger.error(traceback.format_exc())
        return redirect(url_for('system.credentials'))
    return render_template(
        'system/credentials_unlock.html',
        form=form
    )


@system.route(f'/{system.name}/credentials/_lock_credentials', methods=['GET', 'POST'])
def lock_credentials():
    try:
        credential_manager.lock_credentials()
    except Exception:
        logger.error(traceback.format_exc())
        flash("Failed to lock credentials", category='error')
    return redirect(url_for('system.credentials'))

@system.route(f'/{system.name}/credentials/_get_item_info')
def get_item_info():
    info_dict = {}
    group_id = request.args.get('id', 0, type=int)
    group = CredentialGroup.query.filter_by(id=group_id).first()
    credential_list = credential_manager.get_group_credentials(group_id)
    info_dict["group_id"] = group_id
    info_dict["description"] = group.description
    info_dict["service_name"] = group.service_name
    info_dict["service_id"] = group.service_id
    info_dict["time_added"] = group.time_added
    info_dict["credentials"] = []
    for key, value in credential_list.items():
        info_dict["credentials"].append(
            dict(role=key, data=value))

    # return jsonify(info=info_dict)
    # return json.dumps(info_dict)
    return render_template("sidebar/credentials.html", info_dict=info_dict)


@system.route(f'/{system.name}/credentials/_delete', methods=['POST'])
def delete_groups():
    group_id_list = request.get_json().get('item_ids')
    for group_id in group_id_list:
        credential_manager.remove_credentials(group_id)
        # logger.debug(group_id)
    flash("Successfully removed items", category="success")
    return json.dumps({'success': True}), 200, {'ContentType': 'application/json'}


@system.route(f'/{system.name}/credentials/_edit/<int:group_id>', methods=['GET', 'POST'])
def edit_group(group_id):
    credentials = credential_manager.get_group_credentials(group_id)
    credential_list = []
    for key, value in credentials.items():
        credential_list.append({'credential_role': key})
    # credential_list = [{'credential': 't4estthingy'}]
    form = EditCredentialsForm(group_credentials=credential_list)
    for credential_form in form.group_credentials:
        credential_form.credential.label.text = credential_form.credential_role.data
    # for credential in credentials:
    #    form.append_field("test", "testy")
    # form = EditCredentialsForm()
    # for credential in credentials:
    #    form.add_field(credential.credential_role, 'testdata')
    # for credential_form in form.group_credentials:
    #    credential_form.credential.label.text
    if form.validate_on_submit():
        credential_manager.set_group_description(group_id, form.group_description.data)
        for credential_form in form.group_credentials:
            credential_manager.set_credential(group_id, credential_form.credential_role.data,
                                              credential_form.credential.data)
        flash("Credentials have been updated", category='success')
        return redirect(url_for('system.credentials'))
    elif request.method == 'GET':
        form.group_description.data = credential_manager.get_group_description(group_id)
        for credential_form in form.group_credentials:
            # logger.debug("LABEL" + str(credential_form.credential.label.text))
            credential_form.credential.data = credential_manager.get_credential(group_id, credential_form.credential_role.data)
            # logger.debug("DATA" + str(credential_form.credential.data))
        
    return render_template("system/credentials_edit.html", form=form)