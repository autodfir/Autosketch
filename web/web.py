from flask import render_template, jsonify, request, current_app, Flask, redirect, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
import sqlite3
import logging
import os
import json
import rq_dashboard
import redis
from rq import Queue
from timesketch_api_client import config
import subprocess
import yaml
import uuid

from logic import start
from models import User, Task
from db import init_db_command,close_db,init_app
import auth

from typing import Text

CONFIG_FILE = "/etc/autosketch/config.yaml"


app = Flask(__name__, static_folder="static")
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SESSION_COOKIE_NAME'] = 'autosketch_session'

app.teardown_appcontext(close_db)
app.cli.add_command(init_db_command)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

init_app(app)

# try to load config file
try:
    with open(CONFIG_FILE, "r") as stream:
        conf = yaml.safe_load(stream)

        UPLOAD_FOLDER = conf["UPLOAD_FOLDER"]
        LOG_FILE = UPLOAD_FOLDER + '/log.txt'
        ALLOWED_EXTENSIONS = set(['7z', 'zip'])
        APP_IP = conf["APP_IP"]
        APP_PORT = conf["APP_PORT"]
        TS_IP = conf["TS_IP"]
        TS_PORT = conf["TS_PORT"]
        REDIS_IP = conf["REDIS_IP"]
        REDIS_PORT = conf["REDIS_PORT"]
        TS_RC = conf["TS_RC"]
        VELO_USED = conf["VELO_USED"]

        app.config.from_object(rq_dashboard.default_settings)
        app.register_blueprint(rq_dashboard.blueprint, url_prefix="/rq")
        app.config["RQ_DASHBOARD_REDIS_URL"] = "redis://{}:{}".format(REDIS_IP,REDIS_PORT)

except yaml.YAMLError as exc:
        print(exc)
except FileNotFoundError as e:
        print(e)


def get_sketches(username):
    ts = config.get_client(config_path=TS_RC,config_section=username)
    sketches = ts.list_sketches()
    
    sketch_list = []
    for sketch in sketches:
        sketch_list.append({"sketch_id": sketch.id,
                            "sketch_name": sketch.name})
    return sketch_list

    
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/')
@login_required
def index():
    sketches = get_sketches(current_user.name)
    ts_url = f"http://{TS_IP}:{TS_PORT}"
    logging.error("USERNAME: " + current_user.name)

    return render_template("timesketch2.html",

                           title='Autosketch',
                           sketches=sketches,
                           velo_used=VELO_USED,
                           ts_url=ts_url)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/login', methods=["GET","POST"])
def login():
    # TODO redirect if session already established
    # if GET
    if request.method == 'GET':
        return render_template("login.html")

    if request.method == 'POST':
        # get params
        # check credentials
        user = request.form.get('username')
        password = request.form.get('password')

        result = auth.check_credentials(TS_IP,TS_PORT,user,password)

        if result is True:
            
            auth.create_new_token(user,password,TS_IP,TS_PORT,TS_RC)
            
            id = user
            user_obj = User(id=id, name=user)

            # Doesn't exist? Add it to the database.
            if not User.get(id):
                User.create(id, user)

            # Begin user session by logging the user in
            login_user(user_obj)

            return redirect(url_for('index'))
        elif result is False :
            return render_template("login.html", error = "Wrong credentials")
        else:
            return render_template("login.html", error = result)


@app.route('/ts')
@login_required
def ts_redirect():
    
    url = f"http://{TS_IP}:{TS_PORT}"

    return redirect(url)


@app.route('/tasks')
@login_required
def tasks():
    # get current user tasks
    tasks = Task.get_all_by_user(current_user.name)
    return render_template("tasks.html", title='Autosketch', tasks=tasks)


@app.route("/tasks_log", methods=["GET"])
@login_required
def tasks_log():

    task_uuid = request.args.get("task_id")

    log_file = UPLOAD_FOLDER + "/" + task_uuid + ".log"
    # if file doesn't exist return list with that info
    if os.path.exists(log_file):
        with open(log_file) as l:
            logs_lines = l.readlines()
        # to make it more readable remove every Worker_ line and reverse the list
        logs_lines = [x for x in logs_lines if "Worker_" not in x][::-1]

    else:
        logs_lines = ["Log file not found"]
    
    return render_template("logs2.html", title='Autosketch', logs=logs_lines)


# Preparing json config and setting directory structure needed for task to run correctly
@app.route('/uploader', methods=['POST'])
@login_required
def upload_file():

    def run_task2(ts_conf, file=None):
        q = Queue(name="parsers", connection=redis.Redis(host=REDIS_IP, port=REDIS_PORT))
        
        task_uuid = str(uuid.uuid4())
        
        # create directory based on task uuid
        task_dir = UPLOAD_FOLDER + "/" + task_uuid
        os.mkdir(task_dir)

        ts_conf["dir"] = task_dir

        with open(os.path.join(task_dir, "ts_flow.json"), "w") as f:
            json.dump(ts_conf, f, indent=4)

        # case for file upload, file need to be saved in task dir
        if file is not None:
            filename = file.filename
            file.save(os.path.join(task_dir, filename))
            conf_file["file"] = filename

        task = q.enqueue(start, ts_conf, task_uuid, job_timeout=36000)

        Task.create(task_uuid, current_user.name, task.enqueued_at)

        output = f"Task {task_uuid} added to queue at {task.enqueued_at}"
        logging.info("TAKS_OUT:" + output)
        return output

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    error=None
    output=None
    # Load task configuration from POST
    conf_file = request.form.to_dict()
    conf_file['user'] = current_user.name

    parsing_mode = conf_file['parsing_mode']

    # Check if velo parsing mode is selected and process accordingly
    if parsing_mode == 'Velo':
        conf_file['file'] = "ts_" + conf_file['hunt_id'] + ".zip"
        output = run_task2(conf_file)

    # Check if local parsing mode is selected and process accordingly       
    elif parsing_mode == 'Local':
        if os.path.exists(conf_file['dir_path']):
            output = run_task2(conf_file)
            
        else:
            error = 'Local path does not exist'
            
    # Check if out parsing mode selected and process accordingly        
    elif parsing_mode == 'Upload':
        if 'file' not in request.files:
            error = 'No file part in the request'
            
        file = request.files['file']
        if file.filename == '':
            error = 'No file selected for uploading'
        
        if file and allowed_file(file.filename):
            output = run_task2(conf_file,file)
            
        else:
            error = 'Allowed file types are zip and 7z'

    sketches = get_sketches(current_user.name)
    ts_url = f"http://{TS_IP}:{TS_PORT}"
    return render_template("timesketch2.html",
                           title='Autosketch',
                           sketches=sketches,
                           ts_url=ts_url,
                           velo_used=VELO_USED,
                           error=error,
                           output=output)


# api endpoint for getting timelines for a sketch
@app.route('/get_timelines/<sketch_id>')
@login_required
def get_timelines(sketch_id):
    ts = config.get_client(config_path=TS_RC,config_section=current_user.name)
    sketch = ts.get_sketch(int(sketch_id))
    timelines = sketch.list_timelines()
    timeline_list = []
    for timeline in timelines:
        timeline_list.append({"timeline_id": timeline.id,
                              "timeline_name": timeline.name})
    return jsonify(timeline_list)


if __name__ == "__main__":
    app.run(host=APP_IP, port=APP_PORT)