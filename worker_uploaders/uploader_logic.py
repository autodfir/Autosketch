import json
from timesketch_api_client import config
from timesketch_import_client import importer
import logging
import yaml
import time
import traceback

import adjusters

CONFIG_FILE = "/etc/autosketch/config.yaml"
with open(CONFIG_FILE, "r") as stream:
    try:
        conf = yaml.safe_load(stream)
    except yaml.YAMLError as exc:
        print(exc)

UPLOAD_FOLDER = conf["UPLOAD_FOLDER"]
LOG_FILE = UPLOAD_FOLDER + "/log.txt"

TS_RC = conf["TS_RC"]
REDIS_IP = conf["REDIS_IP"]
REDIS_PORT = conf["REDIS_PORT"]


def upload_file_to_timesketch(file_path, timeline, sketch_id, user):
    '''
    Uploads a file (csv/jsonl) to timesketch

    Args:
        file_path (str): path to csv file
        timeline (str): name of timeline
        sketch_id (str): id of sketch
        user (str): user name
    
    '''
    # Strange error, sometimes sketch_id is a tuple
    if type(sketch_id) == tuple:
        sketch_id = sketch_id[0]

    logging.info("Start - Uploading file to timesketch")
    logging.info("Trying to upload to sketch id: " + str(sketch_id))
    try:

        ts = config.get_client(config_path=TS_RC, config_section=user)

        my_sketch = ts.get_sketch(int(sketch_id))

    except Exception as e:
        logging.error("Error - while uploading, cannot get sketch: " + str(e))
        logging.error(str(locals()))
        logging.error(traceback.format_exc())
        return

    try:
        with importer.ImportStreamer() as streamer:
            streamer.set_sketch(my_sketch)
            streamer.set_timeline_name(timeline)

            # loop through file and upload to timesketch
            with open(file_path, 'r') as f:
                for line in f:
                    streamer.add_dict(json.loads(line))

    except Exception as e:
        logging.error("Error -  uploading file to timesketch: " + str(e))
        logging.error(str(locals()))
        logging.error(traceback.format_exc())
    else:
        logging.info("Finished - uploading file to timesketch")

    
    return


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

        ts = config.get_client(config_path=TS_RC, config_section=user)

        logging.info("Trying to upload to sketch id: " + str(sketch_id))

        my_sketch = ts.get_sketch(int(sketch_id))
    except Exception as e:
        logging.error("Error - while uploading, cannot get sketch: " + str(e))
        logging.error(str(locals()))
        logging.error(traceback.format_exc())

    try:
        with importer.ImportStreamer() as streamer:
            streamer.set_sketch(my_sketch)
            streamer.set_timeline_name(timeline)
            streamer.add_file(plaso_storage_path)
            
            error_counter = 0
            while True and error_counter < 5:
                try:
                    status = streamer.state
                except Exception as e:
                    error_counter += 1
                    logging.warning("Catched exceptions while checking status. Error counter: " + str(error_counter))
                    time.sleep(60)
                    continue
                
                logging.info("Indexing status: " + status)
                if status == "SUCCESS":
                    break
                error_counter = 0
                time.sleep(60)

    except Exception as e:
        logging.error("Error - uploading plaso to timesketch: " + str(e))
        logging.error(str(locals()))
        logging.error(traceback.format_exc())
    else:
        if error_counter >= 5:
            logging.error("Error - uploading plaso returned 5 errors in a row. Aborting")
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

        ts = config.get_client(config_path=TS_RC, config_section=user)

        ts.create_sketch(new_sketch_name, description=new_sketch_desc)
        sketches = ts.list_sketches()
        for s in sketches:
            if s.name == new_sketch_name:
                logging.info("Finished - creating new sketch: " + new_sketch_name)
                return s.id
    except Exception as e:
        logging.error("Error - creating new sketch: " + str(e))


def start_uploader(uploader_conf, task_uuid="0-0-0-0-0"):
    '''
    Starts the uploader worker, continuation of autosketch task

    Args:
        uploader_conf (dict): uplaoder configuration
        task_uuid (str): task uuid

    '''
    log_file = UPLOAD_FOLDER + "/" + task_uuid + ".log"
    logging.basicConfig(filename=log_file, level=logging.INFO,
                        format=f'%(asctime)s %(levelname)s {uploader_conf["timeline"]} - %(message)s')

    user = uploader_conf["user"]

    if uploader_conf["existing"] == "No":
        sketch_id = create_sketch(uploader_conf["sketch_new"],
                                  uploader_conf["sketch_desc"],
                                  user)

        uploader_conf["sketch_id_from_ts"] = str(sketch_id)
        uploader_conf["existing"] = "Yes"

    task_directory = uploader_conf["dir"]
    timeline_name = uploader_conf["timeline"]
    sketch_id = uploader_conf["sketch_id_from_ts"]
    file_to_upload = uploader_conf["file_to_upload"]

    if uploader_conf["parser_uploading"] == "evtx_zimmer":
        adjusted_jsonl_path = adjusters.adjust_EZ_EvtxEcmd_jsonl(file_to_upload)
        upload_file_to_timesketch(adjusted_jsonl_path, timeline_name,
                                  sketch_id, user)

    if uploader_conf["parser_uploading"] == "plaso":
        upload_plaso_to_timesketch(user, file_to_upload,
                                   sketch_id, timeline_name)

    if uploader_conf["parser_uploading"] == "without":
        # TODO add possibilty of upload already parsed artifacts
        pass

    logging.info("Finished")
    return True
