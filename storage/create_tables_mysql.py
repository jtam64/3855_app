import mysql.connector
import yaml

with open("app_conf.yml", "r") as f:
    app_config = yaml.safe_load(f.read())

db_conn = mysql.connector.connect(host=app_config["datastore"]["hostname"], user=app_config["datastore"]["user"],
                                  password=app_config["datastore"]["password"], database=app_config["datastore"]["db"])

db_cursor = db_conn.cursor()

try:
    db_cursor.execute('''
        CREATE TABLE IF NOT EXISTS print_success
        (
            id INT NOT NULL AUTO_INCREMENT,
            spool_id VARCHAR(250) NOT NULL,
            printer_id VARCHAR(250) NOT NULL,
            mm_used INTEGER NOT NULL,
            colour VARCHAR(10) NOT NULL,
            trace_id VARCHAR(250) NOT NULL,
            date_created VARCHAR(100) NOT NULL,
            CONSTRAINT print_success_pk PRIMARY KEY (id)
        )
        ''')

    db_cursor.execute('''
        CREATE TABLE IF NOT EXISTS failed_print
        (
            id INT NOT NULL AUTO_INCREMENT,
            spool_id VARCHAR(250) NOT NULL,
            printer_id VARCHAR(250) NOT NULL,
            mm_wasted INTEGER NOT NULL,
            timestamp VARCHAR(100) NOT NULL,
            trace_id VARCHAR(250) NOT NULL,
            date_created VARCHAR(100) NOT NULL,
            CONSTRAINT failed_print_pk PRIMARY KEY (id)
        )
        ''')
    db_conn.commit()
    db_conn.close()
except:
    print("tables exist")
    db_conn.close()
