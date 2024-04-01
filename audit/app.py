import connexion
from pykafka import KafkaClient
import yaml
import logging
import logging.config
import json
from flask_cors import CORS
import os

# initial setup of app and log config file
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")  # if on local
    app_conf_file = "/config/app_conf.yml"
    log_conf_file = "/config/log_conf.yml"

else:
    print("In Dev Environment")  # if on cloud
    app_conf_file = "app_conf.yml"
    log_conf_file = "log_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())  # read app config


with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())  # read log config
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

# log confirmation messages for app and log configuration
logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)


def get_print_success(index: int) -> dict:
    '''Returns data for index of success print event

    Args:
        index (int): The index of a print event

    Returns:
        json: JSON data for print event
    '''

    hostname = "%s:%d" % (app_config["events"]["hostname"],
                          app_config["events"]["port"])  # set hostname from config file
    client = KafkaClient(hosts=hostname)
    # information for Kafka
    topic = client.topics[str.encode(app_config["events"]["topic"])]

    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
                                         consumer_timeout_ms=1000)

    logger.info("Retrieving print success at index %d" % index)
    try:
        for msg in consumer:
            # iterate over every message and return information
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)

            if msg["type"] == "print_success":
                if index == 0:
                    return msg, 200
                else:
                    index -= 1
    except:
        logger.error("No more messages found")

    logger.error("Could not find print success event at index %d" % index)
    return {"message": "Not Found"}, 404


def get_failed_print(index: int) -> dict:
    hostname = "%s:%d" % (app_config["events"]["hostname"],
                          app_config["events"]["port"])  # set hostname from config file
    client = KafkaClient(hosts=hostname)
    # information for Kafka
    topic = client.topics[str.encode(app_config["events"]["topic"])]

    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
                                         consumer_timeout_ms=1000)

    logger.info("Retrieving failed print at index %d" % index)
    try:
        for msg in consumer:
            # iterate over all messages in consumer and return
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)

            if msg["type"] == "failed_print":
                if index == 0:
                    return msg, 200
                else:
                    index -= 1

    except:
        logger.error("No more messages found")

    logger.error("Could not find print success event at index %d" % index)
    return {"message": "Not Found"}, 404


app = connexion.FlaskApp(__name__, specification_dir="")
CORS(app.app, resources={r"/*": {"origins": "*"}})
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8110)
