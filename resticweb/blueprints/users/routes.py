from flask import Blueprint, redirect, url_for, flash, render_template
from flask_login import login_user, current_user, logout_user
from resticweb.blueprints.users.forms import LoginForm
from resticweb.blueprints.users.models import User
from resticweb import bcrypt

users = Blueprint('users', '__name__')

# commented out during development
# @users.route('/', methods=['GET', 'POST'])
@users.route('/login', methods={'GET', 'POST'})
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and bcrypt.check_password_hash(
                user.password,
                form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('main.home'))
        else:
            flash('Wrong username or password', category='error')
    return render_template('login.html', form=form)


@users.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('users.login'))
