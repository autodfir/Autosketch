import requests
import pytest
import time

from timesketch_api_client.client import TimesketchApi
from timesketch_api_client import search

import sys

AS_URL = "http://localhost:5001"
TS_URL = "http://localhost"

def login_test_user():
    #make session
    session = requests.Session()
    #login with test user
    username = "test"
    password = "test"
    data = {'username': username, 'password': password}
    response = session.post(AS_URL + '/login', data=data)
    assert response.status_code == 200
    return session

def create_a_job(session, data,files):
    response = session.post(AS_URL + '/uploader', data=data, files=files)
    assert response.status_code == 200
    return response

def get_job_id(response):
    output_split = response.text.split('<div class="toast-body">')[1].split('</div>')[0]
    #print(output_split)

    job_id = output_split.split('Task ')[1].split(' added to queue')[0]
    return job_id

#check if the server is running
@pytest.mark.parametrize("url", [AS_URL])
def test_server(url):
    response = requests.get(url)
    assert response.status_code == 200

#try to login with test user
@pytest.mark.parametrize("url", [AS_URL])
def test_login_test_user(url):
    username = "test"
    password = "test"
    data = {'username': username, 'password': password}
    response = requests.post(url + '/login', data=data)
    assert response.status_code == 200

# case 1
@pytest.mark.parametrize("url", [AS_URL])
def test_upload_plaso(url):
    
    session = login_test_user()

    #create from data
    data = {'existing': 'No',
            'sketch_new': 'sketch_name',
            'sketch_desc': 'sketch_decription',
            'timeline':'timeline_name',
            'parsing_mode':'Upload',
            'plaso':'on',
            'tagging':'Linux'}
    
    #read file
    file = {'file': open('data/case1.7z', 'rb')}

    #upload file
    response = create_a_job(session, data, file)
    assert "added to queue" in response.text

    job_id = get_job_id(response)

    ts = TimesketchApi(TS_URL, username='test', password='test')

    time.sleep(30)

    #get list of sketches
    sketches = ts.list_sketches()
    sketches = list(sketches)
    #assert if no sketches are returned
    assert len(sketches) > 0
    
    #find sketch with name sketch_name
    sketch_id = None
    for sketch in sketches:
        if sketch.name == data['sketch_new']:
            sketch_id = sketch.id
            break
    
    assert sketch_id is not None

    #get sketch
    sketch = ts.get_sketch(sketch_id=sketch_id)

    #get timeline
    timelines = sketch.list_timelines()
    timeline_id = None
    for timeline in timelines:
        if timeline.name == data['timeline']:
            timeline_id = timeline.id
            break
    assert timeline_id is not None

    #get events
    search_obj = search.Search(sketch)
    search_obj.query_string = '*'

    events = search_obj.dict

    #assert if there are less than 100 events 
    assert len(events['objects']) >= 100


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
