import requests
import logging
import os
import subprocess

from typing import Text


# set logging to info
logging.basicConfig(level=logging.INFO)


def check_credentials(ts_ip: Text, ts_port: Text, username: Text, password: Text) -> bool:
    """
    Check if the credentials are valid
    
    Args:
        ts_ip: Timesketch IP
        ts_port: Timesketch port
        username: Timesketch username
        password: Timesketch password
    
    Return:
        bool: True if the credentials are valid, False otherwise
    
    """

    url = f"http://{ts_ip}:{ts_port}/login/"

    #make new session (i think it is not neccesary, since csrf-token is in html)
    s = requests.Session()

    #make get to URL if it is unreachable catch exception
    try:
        r = s.get(url)
    except requests.exceptions.RequestException as e:
        logging.error(e)
        return None

    #get csrf token from response
    #<meta name=csrf-token content="TOKEN">
    try:
        csrf_token = r.text.split('<meta name=csrf-token content="')[1].split('">')[0]

        logging.info("Status code: " + str(r.status_code))
        #logging.info("Response: " + str(r.text))

        payload = {'username': username, 'password': password, 'csrf_token': csrf_token}
        #logging.info(f"Logging with {username}:{password}")
    
        r = s.post(url, data=payload)
        logging.info("Status code: " + str(r.status_code))

        #check if login was successful
        if not "Sign in" in r.text:
            logging.info("Login successful")
            return True
        else:
            logging.info("Login failed")
            return False
    except requests.exceptions.RequestException as e:
        logging.error(e)
        return "RequestException"
    except IndexError as e:
        logging.error("Could not get csrf token from response - check if Timesketch is running/accessable")
        logging.error(e)
        return "Could not get csrf token from response - check if Timesketch is running/accessable"

def create_new_token(username: Text, password: Text, ts_ip: Text, ts_port, ts_rc) -> bool:

    #if user is already set up in ts_rc return True
    #check if in ts_rc there is a section with username
    #if ts_rc exists
    if os.path.exists(ts_rc):
        with open(ts_rc,"r") as f:
            if f"[{username}]" in f.read():
                logging.info("User already set up, no need to create new token")
                return True

    #remove ~/.timesketch.token if exists
    if os.path.exists(os.path.expanduser("~/.timesketch.token")):
        os.remove(os.path.expanduser("~/.timesketch.token"))
    #remove ~/.timesketchrc if exists
    if os.path.exists(os.path.expanduser("~/.timesketchrc")):
        os.remove(os.path.expanduser("~/.timesketchrc"))

    ts_url = f"http://{ts_ip}:{ts_port}"
    payload = f"{ts_url}\nuserpass\n{username}\n{password}\n"


    #get path to runnig script
    path = os.path.dirname(os.path.realpath(__file__))

    #path to first_auth.py
    first_auth_path = f"{path}/utils/first_auth.py"

    first_run= None
    #if ts_rc doestn exists its first run
    if not os.path.exists(ts_rc):
        first_run = True
    
    if first_run:
        #run first_auth.py with payload as stdin with Popen but without ts_rc
        p = subprocess.Popen(["python3", first_auth_path, username], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(payload.encode())
        #copy ~/.timesketchrc to ts_rc
        os.system(f"cp ~/.timesketchrc {ts_rc}")
        logging.info("First run")
    else:
        #run first_auth.py with payload as stdin with Popen
        p = subprocess.Popen(["python3", first_auth_path, username, ts_rc ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(payload.encode())
        logging.info("Not first run")

        #append first 8 lines of ~/.timesketchrc to ts_rc
        with open(os.path.expanduser("~/.timesketchrc"),"r") as f:
            with open(ts_rc,"a") as f2:
                for i in range(8):
                    f2.write(f.readline())
                    


    logging.info("User creation completed")
    logging.info(out)
    logging.info(err)

    #.timesketch.token should be created in home directory at this point
    if not os.path.exists(os.path.expanduser("~/.timesketch.token")):
        logging.error("Token file not created")
        return None
    
    #token has to be copied to directory or ts_rc and named in format username.token
    token = open(os.path.expanduser("~/.timesketch.token"), "rb").read()

    #get directory of ts_rc
    ts_rc_dir = os.path.dirname(os.path.realpath(ts_rc))

    #create new token file in ts_rc_dir using with
    with open(f"{ts_rc_dir}/{username}.token", "wb") as f:
        f.write(token)

    logging.info(f"Token file created in {ts_rc_dir}/{username}.token ")
    #remove ~/.timesketch.token
    os.remove(os.path.expanduser("~/.timesketch.token"))

    #add token_file_path=new_token_file to ts_rc below [username] using "with"
    with open(ts_rc, "r") as f:
        ts_rc_lines = f.readlines()

    #find line with [username]
    for i in range(len(ts_rc_lines)):
        if ts_rc_lines[i].startswith(f"[{username}]"):
            #add line with token_file_path
            ts_rc_lines.insert(i+1, f"token_file_path={ts_rc_dir}/{username}.token\n")
            break
    
    #write new ts_rc using context managet with
    with open(ts_rc, "w") as ts_rc_file:
        ts_rc_file.writelines(ts_rc_lines)

    

    
    

