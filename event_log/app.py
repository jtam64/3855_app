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

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

if not os.path.exists(app_config["datastore"]["filename"]):
    create_database.main()

DB_ENGINE = create_engine("sqlite:///%s" % app_config["datastore"]["filename"])

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

def get_event_stats():
    logger.info("Request started")
    session = DB_SESSION()

    if session.query(Events).count() < 1:
        return "Statistics do not exist", 404
    else:
        data = session.query(Events)
        for event in data:
            print(event)
    
    return 200


def process_messages():
    hostname = "%s:%d" % (app_config["events"]["hostname"],
                          app_config["events"]["port"])

    # Connect to kafka
    retries_count = 0
    connect_count = app_config["kafka"]["retries"]
    wait = app_config["kafka"]["wait"]

    while retries_count < connect_count:
        try:
            logger.info("Attempting to connect to Kafka")
            client = KafkaClient(hosts=hostname)
            logger.info("Connected to Kafka")
            break
        except:
            time.sleep(wait)
            logger.error(f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
            retries_count += 1

    topic = client.topics[str.encode(app_config["events"]["topic"])]

    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                         reset_offset_on_start=False,
                                         auto_offset_reset=OffsetType.LATEST)

    for msg in consumer:
        session = DB_SESSION()
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)

        message, code = msg["message"], msg["code"]
        event_log = Events(
            message,
            code,
            datetime.datetime.now(),
        )
        session.add(event_log)
        session.commit()
        logger.info("Added to DB")

app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8120)
