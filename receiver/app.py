import connexion
from connexion import NoContent
import requests
import yaml
import logging
import logging.config
import uuid
import datetime
import json
from pykafka import KafkaClient

HEADERS = {"Content-type": "application/json"}

with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')


def print_success(body):
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

    # old post service
    # response = requests.post(app_config["print_success"]["url"], json=request_body, headers=HEADERS)
    # return NoContent, response.status_code
    # logger.info(
    #     f"Returned event print_success response ({trace_id} with status {response.status_code})")

    # return NoContent, response.status_code

    # new post service
    client = KafkaClient(
        hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    producer = topic.get_sync_producer()

    msg = {
        "type": "print_success",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": request_body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(
        f"Returned event print_success response ({trace_id} with status 201")
    return NoContent, 201


def failed_print(body):
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
    # old post service
    # response = requests.post(
    #     app_config["failed_print"]["url"], json=request_body, headers=HEADERS)
    # logger.info(
    #     f"Returned event failed_print response (id: {trace_id} with status {response.status_code})")
    # return NoContent, response.status_code

    # new post service
    client = KafkaClient(
        hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
    topic = client.topics[str.encode(app_config['events']['topic'])]
    producer = topic.get_sync_producer()

    msg = {
        "type": "failed_print",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": request_body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(
        f"Returned event failed_print response ({trace_id} with status 201")
    return NoContent, 201


app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)
