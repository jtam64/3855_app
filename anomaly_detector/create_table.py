import sqlite3
import os
import yaml

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    app_conf_file = "/config/app_conf.yml"

else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())


def main():
    conn = sqlite3.connect(app_config["datastore"]["filename"])
    c = conn.cursor()
    c.execute('''
        CREATE TABLE anomaly
        (id INTEGER PRIMARY KEY ASC, 
        event_id VARCHAR(250) NOT NULL,
        trace_id VARCHAR(250) NOT NULL,
        event_type VARCHAR(100) NOT NULL,
        anomaly_type VARCHAR(100) NOT NULL,
        description VARCHAR(250) NOT NULL,
        date_created VARCHAR(100) NOT NULL)
            ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
        main()