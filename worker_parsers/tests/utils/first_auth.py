from timesketch_api_client_mod import config
import sys



#get first argument

user = sys.argv[1]
#if 2 arguments
if len(sys.argv) == 3:
    ts_rc = sys.argv[2]
    ts = config.get_client(config_path=ts_rc, config_section=user)
else:
    config.get_client(config_section=user)