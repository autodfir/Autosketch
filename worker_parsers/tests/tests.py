import unittest
import json
import yaml
import redis
import pathlib
import shutil 
import uuid
import time
from rq import Queue
from parser_logic import start_parser
import logging
from timesketch_api_client import config, search

CONFIG_FILE = "/etc/autosketch/config.yaml"
import auth

#set up logging so it will prinf info
logging.basicConfig(level=logging.INFO)


#try to load config file
try:
    with open(CONFIG_FILE, "r") as stream:
        conf = yaml.safe_load(stream)

        UPLOAD_FOLDER = conf["UPLOAD_FOLDER"]
        
        TS_IP = conf["TS_IP"]
        TS_PORT = conf["TS_PORT"]
        REDIS_IP = conf["REDIS_IP"]
        REDIS_PORT = conf["REDIS_PORT"]

        TS_RC = conf["TS_RC"]

        
except yaml.YAMLError as exc:
        print(exc)
except FileNotFoundError as e:
        print(e)

class TestWorker(unittest.TestCase):
    queue_parsers = Queue(name="parsers", connection=redis.Redis(host=REDIS_IP,port=REDIS_PORT))
    queue_uploaders = Queue(name="uploaders", connection=redis.Redis(host=REDIS_IP,port=REDIS_PORT))

    def test_000_check_connection(self):
        #TODO
        pass

    def test_010_setup_test_user(self):
        result = auth.create_new_token('test','test',TS_IP,TS_PORT,TS_RC)
        self.assertEqual(result, True)
        return
        
    def test_020_local_plaso(self):
        username = 'test'

        test_dir = 'dba53576-cf32-461f-8de9-abbb221cafae'

        #prepare all data by copying data/plaso/dba53576-cf32-461f-8de9-abbb221cafae to /tmp
        source_path = pathlib.Path(__file__).parent.absolute() / 'data' / 'plaso' / test_dir
        dest_path = pathlib.Path('/tmp') / test_dir
        shutil.copytree(source_path, dest_path,dirs_exist_ok=True)

        #load ts_flow_conf
        with open(dest_path / 'ts_flow.json', 'r') as f:
            ts_flow_conf = json.load(f)

        #modify sketch name, so it differ across tests
        random_id = str(uuid.uuid4())[:8]
        sketch_name = ts_flow_conf['sketch_new'] + '_' + random_id
        ts_flow_conf['sketch_new'] = sketch_name


        #add redis task to queue
        task_uuid = test_dir
        task = self.queue_parsers.enqueue(start_parser, ts_flow_conf, task_uuid, job_timeout=36000)

        while task.result is None:
                pass
        
        #if result is empty string, then it failed
        self.assertNotEqual(task.result, '', 'Task failed')
        self.assertIsNotNone(task.result, 'Task failed')

        upload_task_id = task.result
        #logging.info(f'Result: {upload_task_id}')
        #logging.info(f'Upload task id: {upload_task_id}')
        #get task by id and wait for task to finish
        time.sleep(1)

        upload_task = self.queue_uploaders.fetch_job(upload_task_id)

        self.assertIsNotNone(upload_task, 'Task failed')

        while upload_task.result is None:
                pass

        #sleep for 5 seconds to ensure indexing is done
        time.sleep(5)

        #get sketch id and sketch name by comparing with sketch name
        ts = config.get_client(config_path=TS_RC,config_section=username)
        sketches = ts.list_sketches()
        for sketch in sketches:
            if sketch.name == sketch_name:
                sketch_id = sketch.id
                break
        #sketches_filtered = filter(lambda sketch: sketch.name == sketch_name, sketches)  
          
        #sketch_id = next(sketches_filtered).id

        sketch = ts.get_sketch(sketch_id=sketch_id)
        
        search_obj = search.Search(sketch)
        search_obj.query_string = '*'

        events = search_obj.dict
        #assert if there are less than 90 events (should be 98-100)
        self.assertGreaterEqual(len(events['objects']), 90, 'Less than 90 events found in sketch')
        return

    def test_040_local_evtx(self):
        username = 'test'

        test_dir = 'e0ce02d7-becb-403c-a8f5-8ac3686fc2dd'

        #prepare all data by copying data/evtx/e0ce02d7-becb-403c-a8f5-8ac3686fc2dd to /tmp
        source_path = pathlib.Path(__file__).parent.absolute() / 'data' / 'evtx' / test_dir
        dest_path = pathlib.Path('/tmp') / test_dir
        shutil.copytree(source_path, dest_path,dirs_exist_ok=True)

        #load ts_flow_conf
        with open(dest_path / 'ts_flow.json', 'r') as f:
            ts_flow_conf = json.load(f)

        #modify sketch name, so it differ across tests
        random_id = str(uuid.uuid4())[:8]
        sketch_name = ts_flow_conf['sketch_new'] + '_' + random_id
        ts_flow_conf['sketch_new'] = sketch_name


        #add redis task to queue
        task_uuid = test_dir
        task = self.queue_parsers.enqueue(start_parser, ts_flow_conf, task_uuid, job_timeout=36000)

        #wait for task to finish
        while task.result is None:
                pass
        
        #if result is empty string, then it failed
        self.assertNotEqual(task.result, '', 'Task failed')
        self.assertIsNotNone(task.result, 'Task failed')

        upload_task_id = task.result
        #logging.info(f'Result: {upload_task_id}')
        #logging.info(f'Upload task id: {upload_task_id}')
        #get task by id and wait for task to finish
        time.sleep(1)

        upload_task = self.queue_uploaders.fetch_job(upload_task_id)

        self.assertIsNotNone(upload_task, 'Task failed')

        while upload_task.result is None:
                pass

        #sleep for 5 seconds to ensure indexing is done
        time.sleep(5)
        

        #get sketch id and sketch name by comparing with sketch name
        ts = config.get_client(config_path=TS_RC,config_section=username)
        sketches = ts.list_sketches()

        sketches_filtered = filter(lambda sketch: sketch.name == sketch_name, sketches)  
          
        sketch_id = next(sketches_filtered).id

        sketch = ts.get_sketch(sketch_id=sketch_id)
        
        search_obj = search.Search(sketch)
        search_obj.query_string = '*'

        events = search_obj.dict
        #assert if there are less than 90 events (should be 98-100)
        self.assertGreaterEqual(len(events['objects']), 10000, 'Less than 10000 events found in sketch')

        return

    # def test_900_remove_sketches(self):
    #     username="test"
    #
    #     ts = config.get_client(config_path=TS_RC,config_section=username)
    #     sketches = ts.list_sketches()
    #
    #     for sketch in sketches:
    #             sketch.delete()
    #
    #     sketches = ts.list_sketches()
    #
    #     #check if Generator sketches is empty
    #     self.assertEqual(len(list(sketches)), 0, 'Sketches not deleted')
    #
    #     return

if __name__ == '__main__':
    unittest.main()