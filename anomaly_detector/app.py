import connexion

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
import yaml
from anomaly import Anomaly
import os
import create_table
from pykafka import KafkaClient
from pykafka.common import OffsetType
import time
from threading import Thread
import json
import datetime

import logging
import logging.config

from flask_cors import CORS


def init_stuff():
    # Log the startup parameters
    logger.info("App Conf File: %s" % app_conf_file)
    logger.info("Log Conf File: %s" % log_conf_file)

def get_anomalies():
    pass

def process():
    retries_count = 0
    connect_count = app_config["kafka"]["retries"]
    wait = app_config["kafka"]["wait"]

    # connect to kafka
    while retries_count < connect_count:
        try:
            logger.info("Attempting to connect to Kafka")
            # create producer event for event log service
            CLIENT = KafkaClient(
                hosts=f"{app_config['events']['hostname']}:{app_config['events']['port']}")
            events = CLIENT.topics[str.encode(app_config['events']['topic'])]
            global EVENTS
            EVENTS = events.get_sync_producer()
            break
        except:
            time.sleep(wait)
            logger.error(
                f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
            retries_count += 1
        # information for Kafka
        topic = CLIENT.topics[str.encode(app_config["events"]["topic"])]

        consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                            reset_offset_on_start=False,
                                            auto_offset_reset=OffsetType.LATEST)

        for msg in consumer:
            # Process the messages
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.info("Message: %s" % msg)
            type, datetime, payload = msg["type"], msg["datetime"], msg["payload"]

            print(type, datetime, payload)
            
            session = DB_SESSION()

            logger.info("Added to DB")

            # Commit the offset
            consumer.commit_offsets()

app = connexion.FlaskApp(__name__, specification_dir="")
CORS(app.app, resources={r"/*": {"origins": "*"}})
app.add_api("openapi1.yaml", base_path="/anomaly_detector",
            strict_validation=True, validate_responses=True)

# Read the yaml configuration file
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    CORS(app.app)
    app.app.config['CORS_HEADERS'] = 'Content-Type'
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

# Check if the database exists
if not os.path.exists(app_config["datastore"]["filename"]):
    # Create the database
    create_table.main()

DB_ENGINE = create_engine("sqlite:///%s" % app_config["datastore"]["filename"])

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)



if __name__ == "__main__":
    init_stuff()
    t1 = Thread(target=process)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8900)
