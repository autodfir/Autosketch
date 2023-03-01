import logging
import os
import json
import sys


def adjust_csv_to_timesketch(csv_path):
    '''
    Takes a path to a csv file from EvtxEcmd and adjusts it to the timesketch csv format
    
    Args:
        csv_path (str): path to csv file
    
    Return:
        str: path to adjusted csv file

    '''
    logging.info("Start - adjusting evtx csv to TS")
    try:
        input_file = csv_path
        output_file = csv_path.rsplit(".", 1)[0] + "_adjusted.csv"

        # get first line of input file
        first_line = open(input_file).readline()

        # replace TimeCreated string with datetime string
        first_line = first_line.replace("TimeCreated", "datetime")

        # replace MapDescription string with tag string
        first_line = first_line.replace("MapDescription", "tag")

        # copy input file without first line to output file
        with open(input_file) as f:
            f.readline()  # skip the first line
            with open(output_file, "w") as f2:
                f2.write(f.read())

        # go through file and replace all newlines with ",Creation Time\n"
        with open(output_file, "r") as f:
            with open(output_file + ".tmp", "w") as f2:
                for line in f:
                    line = line.replace("\n", ",Creation Time\n")
                    f2.write(line)

        # rename outputfile to outputfile.tmp
        os.rename(output_file + ".tmp", output_file)

        # append ",timestamp_desc" to first line variable
        first_line = first_line[:-1] + ",timestamp_desc\n"

        # replace Payload string with message string
        first_line = first_line.replace(",Payload,", ",message,")

        # add first_line variable at the beginning of output file
        with open(output_file, "r+") as f:
            content = f.read()
            f.seek(0, 0)
            f.write(first_line + content)

        # unify windows and linux newline characters
        with open(output_file, "r+") as f:
            content = f.read()
            f.seek(0, 0)
            f.write(content.replace("\r", ""))
    except Exception as e:
        logging.error("Error - adjusting evtx csv to TS: " + str(e))
    else:
        logging.info("Finished - adjusting evtx csv to TS")
        return output_file

def adjust_EZ_EvtxEcmd_jsonl(jsonl_path):
    '''
    Takes a path to a jsonl file from EvtxEcmd and adjusts it to the timesketch jsonl format

    Args:
        jsonl_path (str): path to jsonl file

    Return:
        str: path to adjusted jsonl file
    '''
    # gets as an input flatten jsonl file
    # changes fields for every line
    # MapDescription -> tag
    # Payload -> message
    # TimeCreated -> datetime

    # if file doesnt exist exit
    try:
        open(jsonl_path, "r")
    except IOError:
        logging.error("Error - adjusting evtx jsonl to TS - specified file doesnt exist" + jsonl_path)

    #open file for reading
    input_file = open(jsonl_path, "r")

    output_file = jsonl_path.rsplit(".", 1)[0] + "_adjusted.jsonl"

    with open(output_file, "w") as f:
        #read line by line in loop change fields and write to output file
        #doesnt use readlines() because of memory issues
        for line in input_file:
            #strange bug wuth EvtxEcmd adding to first line 3 strange bytes
            # bypass
            if line[0] != "{":
                #cut line to the first {
                line = line[line.find("{"):]
            obj = json.loads(line)
            # only if MapDescription exists
            if "MapDescription" in obj:
                obj["tag"] = obj["MapDescription"]
                del obj["MapDescription"]
            obj["message"] = obj["Payload"]
            del obj["Payload"]
            obj["datetime"] = obj["TimeCreated"]
            del obj["TimeCreated"]
            f.write(json.dumps(obj)+"\n")
        
    logging.info("Finished - adjusting evtx jsonl to TS")
    return output_file
