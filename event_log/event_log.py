from sqlalchemy import Column, Integer, String, DateTime
from base import Base


class Events(Base):
    __tablename__ = "event_log"

    id = Column(Integer, primary_key=True)
    message = Column(String(100), nullable=False)
    code = Column(String(100), nullable=False)
    datetime = Column(DateTime, nullable=False)

    def __init__(self, message, code, datetime):
        self.message = message
        self.code = code
        self.datetime = datetime


    def to_dict(self):
        dict = {}
        dict['id'] = self.id
        dict['message'] = self.message
        dict['code'] = self.code
        dict['datetime'] = self.datetime

        return dict
