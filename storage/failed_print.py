from sqlalchemy import Column, Integer, String, DateTime
from base import Base
import datetime


class FailedPrint(Base):
    __tablename__ = "failed_print"

    id = Column(Integer, primary_key=True)
    spool_id = Column(String(250), nullable=False)
    printer_id = Column(String(250), nullable=False)
    mm_wasted = Column(Integer(), nullable=False)
    timestamp = Column(String(100), nullable=False)
    trace_id = Column(String(250), nullable=False)
    date_created = Column(DateTime, nullable=False)

    def __init__(self, spool_id, printer_id, mm_wasted, timestamp, trace_id):
        self.spool_id = spool_id
        self.printer_id = printer_id
        self.mm_wasted = mm_wasted
        self.timestamp = timestamp
        self.trace_id = trace_id
        self.date_created = datetime.datetime.now() # Sets the date/time record is created

    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['spool_id'] = self.spool_id
        dict['printer_id'] = self.printer_id
        dict['mm_wasted'] = self.mm_wasted
        dict['timestamp'] = self.timestamp
        dict['trace_id'] = self.trace_id
        dict['date_created'] = self.date_created

        return dict
