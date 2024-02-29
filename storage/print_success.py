from sqlalchemy import Column, Integer, String, DateTime
from base import Base
import datetime


class PrintSuccess(Base):
    __tablename__ = "print_success"

    id = Column(Integer, primary_key=True)
    spool_id = Column(String(250), nullable=False)
    printer_id = Column(String(250), nullable=False)
    mm_used = Column(Integer(), nullable=False)
    colour = Column(String(10), nullable=False)
    trace_id = Column(String(250), nullable=False)
    date_created = Column(DateTime, nullable=False)

    def __init__(self, spool_id, printer_id, mm_used, colour, trace_id):
        self.spool_id = spool_id
        self.printer_id = printer_id
        self.mm_used = mm_used
        self.colour = colour
        self.trace_id = trace_id
        # Sets the date/time record is created
        self.date_created = datetime.datetime.now()

    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['spool_id'] = self.spool_id
        dict['printer_id'] = self.printer_id
        dict['mm_used'] = self.mm_used
        dict['colour'] = self.colour
        dict['trace_id'] = self.trace_id
        dict['date_created'] = self.date_created

        return dict
