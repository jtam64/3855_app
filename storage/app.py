from operator import and_
import connexion

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
from print_success import PrintSuccess
from failed_print import FailedPrint
import yaml
import datetime
from pykafka import KafkaClient
import json
from pykafka.common import OffsetType
from threading import Thread
import time
import os

import logging
import logging.config

# Read the yaml configuration file
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

DB_ENGINE = create_engine(f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}", pool_size=20, pool_recycle=3600, pool_pre_ping=True)

Base.metadata.bind = DB_ENGINE

DB_SESSION = sessionmaker(bind=DB_ENGINE)

def init_stuff():
    '''Initializes the application
    '''
    # Log the startup parameters
    logger.info("App Conf File: %s" % app_conf_file)
    logger.info("Log Conf File: %s" % log_conf_file)

    logger.info(
        f"Connecting to DB. Hostname: {app_config['datastore']['hostname']}, Port: {app_config['datastore']['port']}.")
    
def get_print_success(start_timestamp:datetime, end_timestamp:datetime) -> list:
    '''Gets print success events between the start and end timestamps

    Args:
        start_timestamp (datetime): dateime of the start timestamp
        end_timestamp (datetime): datetime of the end timestamp

    Returns:
        list: A list of print success events
    '''
    # Create a session
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(
        start_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    end_timestamp_datetime = datetime.datetime.strptime(
        end_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    # Query the database
    results = session.query(PrintSuccess).filter(
        and_(PrintSuccess.date_created >= start_timestamp_datetime,
             PrintSuccess.date_created < end_timestamp_datetime)
    )

    results_list = []

    for result in results:
        # Append the result to the list
        results_list.append(result.to_dict())

    session.close()

    logger.info(
        f"Query for Print Success after {str(start_timestamp_datetime)} returns {len(results_list)}")

    return results_list, 200

def get_failed_print(start_timestamp:datetime, end_timestamp:datetime) -> list:
    '''Gets failed print events between the start and end timestamps

    Args:
        start_timestamp (datetime): datetime of the start timestamp
        end_timestamp (datetime): datetime of the end timestamp

    Returns:
        list: A list of failed print events
    '''
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(
        start_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    end_timestamp_datetime = datetime.datetime.strptime(
        end_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")

    # Query the database
    results = session.query(FailedPrint).filter(
        and_(FailedPrint.date_created >= start_timestamp_datetime,
             FailedPrint.date_created < end_timestamp_datetime)
    )

    results_list = []

    for result in results:
        results_list.append(result.to_dict())

    session.close()

    logger.info(
        f"Query for Failed Print after {str(start_timestamp_datetime)} returns {len(results_list)}")

    return results_list, 200


def process_messages():
    '''Process incoming messages from Kafka and add to the database
    '''
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

            # create producer event for event log service
            event_log = client.topics[str.encode(app_config['event_log']['topic'])]
            EVENT_LOG = event_log.get_sync_producer()
            msg = {
            "message": "Connected to Kafka and ready to consume messages.",
            "code": "0002",
            }
            msg_str = json.dumps(msg)
            # send message to event log service
            EVENT_LOG.produce(msg_str.encode('utf-8'))
            break
        except:
            time.sleep(wait)
            logger.error(f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
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

        payload = msg["payload"]

        if msg["type"] == "print_success":
            # Store the print success event
            session = DB_SESSION()

            ps = PrintSuccess(payload['spool_id'],
                              payload['printer_id'],
                              payload['mm_used'],
                              payload['colour'],
                              payload['trace_id'],
                              )
            session.add(ps)

            session.commit()
            session.close()

            logger.debug(
                f"Stored event print_success request with a trace id of {payload['trace_id']}")
        elif msg["type"] == "failed_print":
            # Store the failed print event
            session = DB_SESSION()

            fp = FailedPrint(payload['spool_id'],
                             payload['printer_id'],
                             payload['mm_wasted'],
                             payload['timestamp'],
                             payload['trace_id'],
                             )

            session.add(fp)

            session.commit()
            session.close()

            logger.debug(
                f"Stored event failed_print request with a trace id of {payload['trace_id']}")

        consumer.commit_offsets()


app = connexion.FlaskApp(__name__, specification_dir="")
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_stuff()
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8090)
