import connexion
from connexion import NoContent
# import requests
import yaml
import logging
import logging.config
import uuid
import datetime
import json
from pykafka import KafkaClient
import time
import os

HEADERS = {"Content-type": "application/json"}

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", base_path="/receiver",
            strict_validation=True, validate_responses=True)

# initial setup of logging configuration and app configuration
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

retries_count = 0
connect_count = app_config["kafka"]["retries"]
wait = app_config["kafka"]["wait"]

# connect to kafka
while retries_count < connect_count:
    try:
        logger.info("Attempting to connect to Kafka")
        CLIENT = KafkaClient(
            hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
        topic = CLIENT.topics[str.encode(app_config['events']['topic'])]
        PRODUCER = topic.get_sync_producer()
        logger.info("Connected to client")
        break
    except:
        time.sleep(wait)
        logger.error(
            f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
        retries_count += 1


def init_stuff():
    # Log the startup parameters
    logger.info("App Conf File: %s" % app_conf_file)
    logger.info("Log Conf File: %s" % log_conf_file)

    # create producer event for event log service
    event_log = CLIENT.topics[str.encode(app_config['event_log']['topic'])]
    EVENT_LOG = event_log.get_sync_producer()
    msg = {
        "message": "Connected to Kafka and ready to receive messages.",
        "code": "0001",
    }
    msg_str = json.dumps(msg)
    # send message to event log
    EVENT_LOG.produce(msg_str.encode('utf-8'))


def print_success(body: dict):
    '''Receives a print success event

    Args:
        body (dict): The print success event

    Returns:
        NoContent: Returns a 201 status code
    '''
    trace_id = str(uuid.uuid4())
    request_body = {
        "spool_id": body["spool_id"],
        "printer_id": body["printer_id"],
        "mm_used": body["mm_used"],
        "colour": body["colour"],
        "trace_id": trace_id,
    }
    logger.info(
        f"Received event print_success request with a trace id of {trace_id}")

    # new post service
    msg = {
        "type": "print_success",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": request_body
    }
    msg_str = json.dumps(msg)
    # send message to event log
    PRODUCER.produce(msg_str.encode('utf-8'))

    logger.info(
        f"Returned event print_success response ({trace_id} with status 201")
    return NoContent, 201


def failed_print(body: dict):
    '''Receives a failed print event

    Args:
        body (dict): The failed print event

    Returns:
        NoContent: Returns a 201 status code
    '''
    trace_id = str(uuid.uuid4())
    request_body = {
        "spool_id": body["spool_id"],
        "printer_id": body["printer_id"],
        "mm_wasted": body["mm_wasted"],
        "timestamp": body["timestamp"],
        "trace_id": trace_id,
    }
    logger.info(
        f"Received event failed_print request with a trace id of {trace_id}")

    # new post service
    msg = {
        "type": "failed_print",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": request_body
    }
    msg_str = json.dumps(msg)
    # send message to event log
    PRODUCER.produce(msg_str.encode('utf-8'))

    logger.info(
        f"Returned event failed_print response ({trace_id} with status 201")
    return NoContent, 201

if __name__ == "__main__":
    init_stuff()
    app.run(port=8080)
