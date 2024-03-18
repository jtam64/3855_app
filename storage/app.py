from operator import and_
import connexion
from connexion import NoContent

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


import logging
import logging.config

with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

with open("log_conf.yml", "r") as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

DB_ENGINE = create_engine(
    f"mysql+pymysql://{app_config['datastore']['user']}:{app_config['datastore']['password']}@{app_config['datastore']['hostname']}:{app_config['datastore']['port']}/{app_config['datastore']['db']}")

Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)

logger.info(
    f"Connecting to DB. Hostname: {app_config['datastore']['hostname']}, Port: {app_config['datastore']['port']}.")

# Old post requests
# def print_success(body):
#     session = DB_SESSION()

#     ps = PrintSuccess(body['spool_id'],
#                       body['printer_id'],
#                       body['mm_used'],
#                       body['colour'],
#                       body['trace_id'],
#                       )
#     session.add(ps)

#     session.commit()
#     session.close()

#     logger.debug(
#         f"Stored event print_success request with a trace id of {body['trace_id']}")
# return NoContent, 201


def get_print_success(start_timestamp, end_timestamp):
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(
        start_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    end_timestamp_datetime = datetime.datetime.strptime(
        end_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    results = session.query(PrintSuccess).filter(
        and_(PrintSuccess.date_created >= start_timestamp_datetime,
             PrintSuccess.date_created < end_timestamp_datetime)
    )

    results_list = []

    for result in results:
        results_list.append(result.to_dict())

    session.close()

    logger.info(
        f"Query for Print Success after {str(start_timestamp_datetime)} returns {len(results_list)}")

    return results_list, 200

# Old post requests
# def failed_print(body):
#     session = DB_SESSION()

#     fp = FailedPrint(body['spool_id'],
#                      body['printer_id'],
#                      body['mm_wasted'],
#                      body['timestamp'],
#                      body['trace_id'],
#                      )

#     session.add(fp)

#     session.commit()
#     session.close()

#     logger.debug(
#         f"Stored event failed_print request with a trace id of {body['trace_id']}")

#     return NoContent, 201


def get_failed_print(start_timestamp, end_timestamp):
    session = DB_SESSION()
    start_timestamp_datetime = datetime.datetime.strptime(
        start_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")
    end_timestamp_datetime = datetime.datetime.strptime(
        end_timestamp, "%Y-%m-%dT%H:%M:%S.00%f+00:00")

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
    # New post requests
    hostname = "%s:%d" % (app_config["events"]["hostname"],
                          app_config["events"]["port"])
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config["events"]["topic"])]

    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                                         reset_offset_on_start=False,
                                         auto_offset_reset=OffsetType.LATEST)

    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)

        payload = msg["payload"]

        if msg["type"] == "print_success":
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
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(port=8090)
