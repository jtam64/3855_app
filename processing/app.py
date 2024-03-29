from operator import and_
import connexion
from connexion import NoContent

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from base import Base
import yaml
import datetime
import json
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from stats import Stats
import os
import create_database
from pykafka import KafkaClient
import time

import logging
import logging.config

from flask_cors import CORS

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

if not os.path.exists(app_config["datastore"]["filename"]):
    create_database.main()

DB_ENGINE = create_engine("sqlite:///%s" % app_config["datastore"]["filename"])

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

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
        event_log = CLIENT.topics[str.encode(app_config['event_log']['topic'])]
        global EVENT_LOG
        EVENT_LOG = event_log.get_sync_producer()
        break
    except:
        time.sleep(wait)
        logger.error(f"Connection failed. Retrying after {wait}. Attempts: {retries_count}/{connect_count}")
        retries_count += 1

def init_stuff():
    logger.info("App Conf File: %s" % app_conf_file)
    logger.info("Log Conf File: %s" % log_conf_file)

    msg = {
    "message": "Ready to begin processing.",
    "code": "0003",
    }
    msg_str = json.dumps(msg)
    EVENT_LOG.produce(msg_str.encode('utf-8'))

def get_stats():
    logger.info("Request started")

    session = DB_SESSION()

    if session.query(Stats).count() < 1:
        return "Statistics do no exist", 404
    else:
        existing_data = session.query(Stats).order_by(
            Stats.last_updated.desc())[0]
        information = {
            "num_print_success": existing_data.num_print_success,
            "mm_used": existing_data.mm_used,
            "num_failed_print": existing_data.num_failed_print,
            "total_mm_wasted": existing_data.total_mm_wasted,
            "last_updated": existing_data.last_updated,
        }
        logger.debug(information)
        logger.info("Request complete")

        return information, 200


def populate_stats():
    logger.info("Start Periodic Processing")

    session = DB_SESSION()

    # Get todays date in proper format
    today = datetime.datetime.now()
    today = datetime.datetime.strftime(today, "%Y-%m-%dT%H:%M:%S.00%f%z")
    today = today + "+00:00"

    if session.query(Stats).count() < 1:
        # If no values exist in db
        num_print_success = 0
        total_mm_used = 0
        num_failed_print = 0
        total_mm_wasted = 0
        last_updated = "1000-1-1T1:1:1.001000+00:00"
    else:
        # If values exist in db
        existing_data = session.query(Stats).order_by(
            Stats.last_updated.desc())[0]
        num_print_success = existing_data.num_print_success
        total_mm_used = existing_data.mm_used
        num_failed_print = existing_data.num_failed_print
        total_mm_wasted = existing_data.total_mm_wasted
        last_updated = datetime.datetime.strftime(
            existing_data.last_updated, "%Y-%m-%dT%H:%M:%S.00%f") + "+00:00"

    # send get requests
    success_results = requests.get(
        app_config["eventstore"]["url"] + "/print_success", params={"start_timestamp": last_updated, "end_timestamp": today})
    failed_results = requests.get(
        app_config["eventstore"]["url"] + "/failed_print", params={"start_timestamp": last_updated, "end_timestamp": today})

    # Assign variables to request body and status code
    success_body, success_code = success_results.json(), success_results.status_code
    failed_body, failed_code = failed_results.json(), failed_results.status_code

    if success_code == 200 and failed_code == 200:
        # If status code ok evaluate the data
        num_print_success += len(success_body)
        total_mm_used += sum(x["mm_used"] for x in success_body)
        num_failed_print += len(failed_body)
        total_mm_wasted += sum(x["mm_wasted"] for x in failed_body)
    
    # send message to event log service if number of events exceeds limit
    try:
        limit = app_config["event_log"]["limit"]    # if parameter is passed
    except:
        limit = 25                                  # if no parameter is passed, default 25
    if sum([len(success_body), len(failed_body)]) >= limit:
        msg = {
            "message": f"Number of events exceeded limit: {limit}.",
            "code": "0004",
            }
        msg_str = json.dumps(msg)
        EVENT_LOG.produce(msg_str.encode('utf-8'))
        EVENT_LOG.produce(f" Code 0004")

        # Log information received
        logger.info(
            f"Total number of events received: {len(success_body) + len(failed_body)}")

        # add new entry to db
        stats = Stats(
            num_print_success,
            total_mm_used,
            num_failed_print,
            total_mm_wasted,
            datetime.datetime.strptime(
                today.split("+")[0], "%Y-%m-%dT%H:%M:%S.00%f")
        )
        session.add(stats)
        session.commit()

        # log other info
        trace_ids = [x["trace_id"] for x in success_body] + \
            [x["trace_id"] for x in failed_body]

        for trace in trace_ids:
            logger.debug(f"Received event with trace id: {trace}")
        logger.debug(
            f"Update to date number of print success {num_print_success} with {total_mm_used} and number of failed prints {num_failed_print} with {total_mm_wasted}")
        logger.info("End of period processing")
    else:
        # otherwise log an error
        logger.warning(f"Error occured when fetching data")

    session.close()


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,
                  'interval',
                  seconds=app_config['scheduler']['period_sec'])
    sched.start()


app = connexion.FlaskApp(__name__, specification_dir="")
CORS(app.app, resources={r"/*": {"origins": "*"}})
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_stuff()
    init_scheduler()
    app.run(port=8100)
