import sqlite3

conn = sqlite3.connect('stats.sqlite')

c = conn.cursor()
c.execute('''
          CREATE TABLE stats
          (id INTEGER PRIMARY KEY ASC, 
           num_print_success INTEGER NOT NULL,
           mm_used INTEGER NOT NULL,
           num_failed_print INTEGER NOT NULL,
           total_mm_wasted INTEGER NOT NULL,
           last_updated VARCHAR(100) NOT NULL)
          ''')

conn.commit()
conn.close()
