import connexion

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
import yaml
from pykafka import KafkaClient
from pykafka.common import OffsetType
from threading import Thread
import os
import time
import json
import create_database
from event_log import Events
import datetime

import logging
import logging.config
from flask_cors import CORS

# initial setup of logging configuration and app configuration
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
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
    create_database.main()

# Create the database connection
DB_ENGINE = create_engine("sqlite:///%s" % app_config["datastore"]["filename"])

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)


def init_stuff():
    # Log the startup parameters
    logger.info("App Conf File: %s" % app_conf_file)
    logger.info("Log Conf File: %s" % log_conf_file)


def get_event_stats() -> dict:
    '''Returns the statistics of all events

    Returns:
        dict: The statistics of all events
    '''
    logger.info("Request started")
    session = DB_SESSION()

    if session.query(Events).count() < 1:
        # No data in the database
        return "Statistics do not exist", 404
    else:
        # Get the data
        data = session.query(Events)

        vals = {"0001": "one", "0002": "two", "0003": "three", "0004": "four"}
        final = {}

        for event in data:
            # Calculate the statistics
            code = vals[event.code]
            try:
                final[code] += 1
            except:
                final[code] = 1
    logger.info("Returning values")
    return final, 200


def process_messages():
    '''Process incoming messages from Kafka and add to the database
    '''
    hostname = "%s:%d" % (app_config["events"]["hostname"],
                          app_config["events"]["port"])  # Connect to kafka

    # Connect to kafka
    retries_count = 0
    connect_count = app_config["kafka"]["retries"]
    wait = app_config["kafka"]["wait"]

    while retries_count < connect_count:
        # Try to connect to Kafka
        try:
            logger.info("Attempting to connect to Kafka")
            client = KafkaClient(hosts=hostname)
            logger.info("Connected to Kafka")
            break
        except:
            time.sleep(wait)
            logger.error(
                f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
            retries_count += 1

    # information for Kafka
    topic = client.topics[str.encode(app_config["events"]["topic"])]

    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                         reset_offset_on_start=False,
                                         auto_offset_reset=OffsetType.LATEST)

    for msg in consumer:
        # Process the messages
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        message, code = msg["message"], msg["code"]

        session = DB_SESSION()
        event_log = Events(
            message,
            code,
            datetime.datetime.now(),
        )
        # Add to the database
        session.add(event_log)
        session.commit()
        logger.info("Added to DB")

        # Commit the offset
        consumer.commit_offsets()

app = connexion.FlaskApp(__name__, specification_dir="")
CORS(app.app, resources={r"/*": {"origins": "*"}})
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_stuff()
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8120)
