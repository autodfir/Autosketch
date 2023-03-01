import py7zr
import zipfile
import magic

import json
from timesketch_api_client import config
from timesketch_import_client import importer
import logging
import subprocess
import os
import pyvelociraptor
import redis
from rq import Queue
import yaml
import time
import re

import boto3 #s3 library


from uploader_logic import start_uploader


from fetch import run_velo_fetch

CONFIG_FILE = "/etc/autosketch/config.yaml"
with open(CONFIG_FILE, "r") as stream:
    try:
        conf = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

UPLOAD_FOLDER = conf["UPLOAD_FOLDER"]
LOG_FILE = UPLOAD_FOLDER + "/log.txt"
ZIMMERMAN_PATH = "/app"
DOTNET_PATH = '/root/.dotnet/dotnet'

TS_RC = conf["TS_RC"]
REDIS_IP = conf["REDIS_IP"]
REDIS_PORT = conf["REDIS_PORT"]

VELO_USED = conf["VELO_USED"]
S3_STS_USED = conf["S3_STS_USED"]

if VELO_USED:
    VELO_API_CONF_PATH = conf["VELO_API_CONF_PATH"]
    try:
        VELO_API_CONF = pyvelociraptor.LoadConfigFile(VELO_API_CONF_PATH)
    except Exception as e:
        logging.error("Error - loading velociraptor api config: " + str(e))
        VELO_USED = False


# TODO Password protected archives
def unzip(archive_path):
    '''
    Unzips a 7z or zip archive to the same directory
    
    Args: 
        archive_path (str): absolute path to archive
    '''
    logging.info("Start - Unzipping " + archive_path)
    try:
        if magic.from_file(archive_path, mime=True) == "application/x-7z-compressed":
            with py7zr.SevenZipFile(archive_path, mode='r') as z:
                z.extractall(path=archive_path.rsplit(".", 1)[0])
        if magic.from_file(archive_path, mime=True) == "application/zip":
            with zipfile.ZipFile(archive_path) as file:
                file.extractall(archive_path.rsplit(".", 1)[0])
    except Exception as e:
        logging.error("Error - unzipping " + archive_path + ": " + str(e))
    else:
        logging.info("Finished - Unzipped " + archive_path)

def download_from_s3(aws_access_key, aws_secret_key, s3_path, out_dir, sts_token=None):
    '''
    Downloads a file from s3

    Args:
        aws_access_key (str): aws access key
        aws_secret_key (str): aws secret key
        s3_path (str): path to file in s3
        out_dir (str): path to output directory
        sts_token (str): sts token (optional)

    Return:
        str: path to downloaded file
    '''
    logging.info("Start - Downloading " + s3_path + " from s3")
    bucket = re.search(r"s3://(.*?)/", s3_path).group(1)
    zip_path = re.search(r"s3://.*?/(.*)", s3_path).group(1)

    try:
        if sts_token:
            s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key, aws_session_token=sts_token)
        else:
            s3 = boto3.client('s3', aws_access_key_id=aws_access_key, aws_secret_access_key=aws_secret_key)
        s3.download_file(bucket, zip_path, out_dir + "/" + s3_path.split("/")[-1]) 

    except Exception as e:
        logging.error("Error - downloading " + s3_path + " from s3: " + str(e))
        return None
    else:
        logging.info("Finished - Downloaded " + s3_path + " from s3")
        return out_dir + "/" + s3_path.split("/")[-1]

def run_zimmer_evtx(artifacts_path, out_dir, out_filename):
    '''
    Runs the zimmerman evtx parser on a directory of evtx files

    Args:
        artifacts_path (str): path to directory of evtx files
        out_dir (str): path to output directory
        out_filename (str): name of output file without extension

    Return:
        str: path to output csv file

    '''

    logging.info("Start - running Zimmerman evtx parser")
    try:
        cmd = DOTNET_PATH + " " + ZIMMERMAN_PATH + "/EvtxeCmd/EvtxECmd.dll -d " + artifacts_path\
              + " --csv " + out_dir + " --csvf \"" + out_filename + ".csv\""
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        #communicate prrocess and save stdout to output variable
        output = p.communicate()[0].decode('utf-8')
        logging.info(output)
        
    except Exception as e:
        logging.error("Error - running Zimmerman evtx parser : " + str(e))
    else:
        logging.info("Finished - Zimmerman evtx parser")
        return out_dir + "/" + out_filename + ".csv"

def run_zimmer_evtx_json(artifacts_path, out_dir, out_filename):
    '''
    Runs the zimmerman evtx parser on a directory of evtx files

    Args:
        artifacts_path (str): path to directory of evtx files
        out_dir (str): path to output directory
        out_filename (str): name of output file without extension

    Return:
        str: path to output jsonl file

    '''

    logging.info("Start - running Zimmerman evtx parser")
    try:
        cmd = DOTNET_PATH + " " + ZIMMERMAN_PATH + "/EvtxeCmd/EvtxECmd.dll -d " + artifacts_path\
              + " --json " + out_dir + " --jsonf \"" + out_filename + ".jsonl\""
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        #communicate prrocess and save stdout to output variable
        output = p.communicate()[0].decode('utf-8')
        logging.info(output)
        
    except Exception as e:
        logging.error("Error - running Zimmerman evtx parser : " + str(e))
    else:
        logging.info("Finished - Zimmerman evtx parser")
        return out_dir + "/" + out_filename + ".jsonl"

def upload_file_to_timesketch2(file_path, timeline, sketch_id, user):
    '''
    Uploads a file (csv/jsonl) to timesketch

    Args:
        file_path (str): path to csv file
        timeline (str): name of timeline
        sketch_id (str): id of sketch
        user (str): user name
    
    '''
    #Strange error, sometimes sketch_id is a tuple
    if type(sketch_id) == tuple:
        sketch_id = sketch_id[0]

    logging.info("Start - Uploading file to timesketch")
    logging.info("Trying to upload to sketch id: " + str(sketch_id) )
    try:

        ts = config.get_client(config_path=TS_RC,config_section=user)

        my_sketch = ts.get_sketch(int(sketch_id))

        with importer.ImportStreamer() as streamer:
            streamer.set_sketch(my_sketch)
            streamer.set_timeline_name(timeline)
            streamer.set_filesize_threshold(200000000)
            streamer.set_entry_threshold(100000)
            streamer.add_file(file_path)

            while True:
                status = streamer.state
                logging.info("Indexing status: " + status)
                if status == "SUCCESS":
                    break
                elif status == "FAILURE":
                    logging.error("Error - Uploading file to timesketch")
                    break
                time.sleep(60)

    except Exception as e:
        logging.error("Error -  uploading file to timesketch: " + str(e))
    else:
        logging.info("Finished - uploading file to timesketch")

def run_plaso(artifacts_path, out_dir, plaso_storage):
    '''
    Runs plaso on a directory of artifacts

    Args:
        artifacts_path (str): path to directory of artifacts
        out_dir (str): path to output directory
        plaso_storage (str): name of plaso storage file

    '''

    logging.info("Start - running plaso")
    try:
        #cmd = "log2timeline.py --parsers !winevtx --logfile " + out_dir + "/out.log --storage-file " + out_dir + "/" + plaso_storage + " " + artifacts_path
        cmd = "log2timeline.py --status_view linear --parsers !winevtx --storage-file " + out_dir + "/" + plaso_storage + " " + artifacts_path
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        #communicate prrocess and save stdout to output variable
        output = p.communicate()[0].decode('utf-8')

        logging.info(output)

        logging.info("Finished - running plaso")

    except Exception as e:
        logging.error("Error - worker - running plaso: " + str(e))
    else:
        logging.info("Finished - worker - running plaso")

def run_tagging(out_dir, plaso_storage, tagging_os):
    '''
    Runs tagging on a plaso storage file

    Args:
        out_dir (str): path to output directory
        plaso_storage (str): name of plaso storage file
        tagging_os (str): OS of the artifacts

    '''
    logging.info("Start - running tagging")
    try:
        p = None
        if tagging_os == "Windows":
            cmd = "psort.py --status_view linear --analysis tagging --tagging-file /usr/share/plaso/tag_windows.txt -o null " + out_dir + "/" + plaso_storage
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # communicate prrocess and save stdout to output variable
            output = p.communicate()[0].decode('utf-8')

        elif tagging_os == "Linux":
            cmd = "psort.py --status_view linear --analysis tagging --tagging-file /usr/share/plaso/tag_linux.txt -o null " + out_dir + "/" + plaso_storage
            p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # communicate prrocess and save stdout to output variable
            output = p.communicate()[0].decode('utf-8')
            
        else:
            logging.info("Tagging skipped - not chosen by the user")
            return 

        
        logging.info(output)
        logging.info("Finished - running tagging")
        return 

    except Exception as e:
        logging.error("Error - running tagging: " + str(e))

def upload_plaso_to_timesketch(user, plaso_storage_path, sketch_id, timeline):
    '''
    Uploads a plaso storage file to timesketch

    Args:
        user (str): username
        plaso_storage_path (str): path to plaso storage file
        sketch_id (str): id of sketch
        timeline (str): name of timeline

    '''
    # Strange error, sometimes sketch_id is a tuple
    if type(sketch_id) == tuple:
        sketch_id = sketch_id[0]

    logging.info("Start - uploading plaso to timesketch")
    try:

        ts = config.get_client(config_path=TS_RC,config_section=user)
        
        logging.info("Trying to upload to sketch id: " + str(sketch_id) )
        
        my_sketch = ts.get_sketch(int(sketch_id))
        
        with importer.ImportStreamer() as streamer:
            streamer.set_sketch(my_sketch)
            streamer.set_timeline_name(timeline)
            streamer.add_file(plaso_storage_path)
            while True:
                status = streamer.state
                logging.info("Indexing status: " + status)
                if status == "SUCCESS":
                    break
                time.sleep(60)

    except Exception as e:
        logging.error("Error - uploading plaso to timesketch: " + str(e))
    else:
        logging.info("Finished - uploading plaso to timesketch")


def create_sketch(new_sketch_name, new_sketch_desc, user):
    '''
    Creates a new sketch in timesketch

    Args:
        new_sketch_name (str): name of new sketch
        new_sketch_desc (str): description of new sketch
        user (str): user name

    '''
    logging.info("Start - Creating new sketch : " + new_sketch_name)
    try:

        ts = config.get_client(config_path=TS_RC,config_section=user)

        ts.create_sketch(new_sketch_name, description=new_sketch_desc)
        sketches = ts.list_sketches()
        for s in sketches:
            if s.name == new_sketch_name:
                logging.info("Finished - creating new sketch: " + new_sketch_name)
                return s.id
    except Exception as e:
        logging.error("Error - creating new sketch: " + str(e))


def create_hunt_download(hunt_id):
    try:
        cmd = "pyvelociraptor --config /app/velo_api.config.yaml 'LET result <=  create_hunt_download(hunt_id=\"" +\
              hunt_id + "\", base=\"ts_\", wait=\"True\") SELECT * FROM result'"
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        output = p.stdout.read()
        logging.info(output)

        #TODO what if there is error in the output? Or empty output? Etc...
        if "Hunt not found" in output:
            logging.error("Error - Hunt not found")
            return "Hunt not found"
        else:
            logging.info("Hunt scheduled for download")
            return "Scheduled"

    except Exception as e:
        logging.error("Error - creating hunt download: " + str(e))
        return "error"


def start_parser(parser_conf, task_uuid="0-0-0-0-0"):
    '''
    Starts the worker, entrypoint of new autosketch task

    Args:
        parser_conf (dict): parser_conf configuration
        task_uuid (str): task uuid

    Returns:
        bool: True if success, False if error

    '''
    log_file = UPLOAD_FOLDER + "/" + task_uuid + ".log"
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format=f'%(asctime)s %(levelname)s {parser_conf["timeline"]} - %(message)s')
    

    #with open(task_dir + "/parser_conf.json") as f:
    #    parser_conf = json.load(f)

    q = Queue(name="uploaders", connection=redis.Redis(host=REDIS_IP, port=REDIS_PORT))


    parsing_mode = parser_conf["parsing_mode"]
    task_directory = parser_conf["dir"]
    timeline_name = parser_conf["timeline"]


    if parsing_mode == "Velo":
        if VELO_USED:
            logging.info("Velociraptor library used - tasks will be queued for every host")
            logging.info("Start - creating hunt download")
            res = create_hunt_download(parser_conf["hunt_id"])
            if res == "Scheduled":
                logging.info("Finished - creating hunt download")
                vfs = "downloads/hunts/" + parser_conf["hunt_id"] + "/" + parser_conf["file"]
                full_path = parser_conf["dir"] + "/" + parser_conf["file"]
                logging.info("Start - fetching velociraptor hunt results")
                run_velo_fetch(VELO_API_CONF, vfs, full_path)
                logging.info("Finished - fetching velociraptor hunt results")
                unzip(full_path)
                artifacts_dir = full_path.rsplit(".", 1)[0] + "/clients"
                
                hosts = os.listdir(artifacts_dir)
                hosts_paths = [artifacts_dir + "/" + host for host in hosts]

                new_conf_file = parser_conf
                for host_path in hosts_paths:
                    new_conf_file["timeline"] = timeline_name + "_" + host_path.split("/")[-1]
                    new_conf_file["parsing_mode"] = "Post-Velo"
                    new_conf_file["dir_path"] = host_path + "/collections"
                    new_conf_file["file"] = ""
                    with open(os.path.join(host_path, "ts_flow.json"), "w") as f:
                        json.dump(new_conf_file, f, indent=4)
                    q = Queue(connection=redis.Redis(host=REDIS_IP,port=REDIS_PORT))
                    q.enqueue(start_parser, host_path, job_timeout=36000)
                    logging.info("Queued analysis of " + host_path.split("/")[-1] + " host")
            return True
        else:
            logging.info("Velociraptor not set up - please provide velo api config and fill app config accordingly")
            logging.info("Aborting analysis")
            return False
    
    if parsing_mode == "S3":
        logging.info("Start - fetching s3 artifacts")
        s3_access_key = parser_conf["s3_access_key"]
        s3_secret_key = parser_conf["s3_secret_key"]
        s3_path = parser_conf["s3_path"]
        if S3_STS_USED:
            logging.info("S3 STS used")
            zip_path = download_from_s3(s3_access_key, s3_secret_key, s3_path, task_directory, sts_token=parser_conf["s3_sts_token"])
        else:
            zip_path = download_from_s3(s3_access_key, s3_secret_key, s3_path, task_directory)

        if zip_path:
            logging.info("Finished - fetching s3 artifacts")
            unzip(zip_path)
            artifacts_path = task_directory 
            plaso_storage = "out.plaso"
        else:
            logging.error("Error - fetching s3 artifacts")
            return False

    if parsing_mode == "Upload": 
        zip_filename = parser_conf["file"] #TODO directory straversal ?
        full_path = task_directory + "/" + zip_filename
        unzip(full_path)
        artifacts_path = task_directory + "/" + zip_filename.rsplit(".", 1)[0]
        plaso_storage = zip_filename.rsplit(".", 1)[0] + ".plaso"
    
    elif parsing_mode == "Post-Velo" or parsing_mode == "Local":
        artifacts_path = parser_conf["dir_path"]
        plaso_storage = timeline_name + ".plaso"

    # variables needed to upload data
    # sketch_id = parser_conf["sketch_id_from_ts"]
    # user = parser_conf["user"]
    if "evtx" in parser_conf:
        #out_csv_path = run_zimmer_evtx(artifacts_path, task_directory, timeline_name)
        #adjusted_csv_path = adjusters.adjust_csv_to_timesketch(out_csv_path)
        
        parser_conf["file_to_upload"] = run_zimmer_evtx_json(artifacts_path, task_directory, timeline_name)
        parser_conf["parser_uploading"] = "evtx_zimmer"
        q.enqueue(start_uploader, parser_conf, task_uuid, job_timeout=36000)
        
        # upload_file_to_timesketch(adjusted_jsonl_path, timeline_name,
        #                          sketch_id, user)

    if "plaso" in parser_conf:
        run_plaso(artifacts_path, task_directory, plaso_storage)
        run_tagging(task_directory, plaso_storage, parser_conf["tagging"])
        parser_conf["file_to_upload"] = task_directory + "/" + plaso_storage
        parser_conf["parser_uploading"] = "plaso"
        q.enqueue(start_uploader, parser_conf, task_uuid, job_timeout=36000)


        # upload_plaso_to_timesketch(user, task_directory + "/" + plaso_storage,
        #                            sketch_id, timeline_name)

    logging.info("Finished")
    return True



