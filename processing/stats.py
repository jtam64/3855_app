from sqlalchemy import Column, Integer, DateTime
from base import Base


class Stats(Base):
    """ Processing Statistics """
    __tablename__ = "stats"
    id = Column(Integer, primary_key=True)
    num_print_success = Column(Integer, nullable=False)
    mm_used = Column(Integer, nullable=True)
    num_failed_print = Column(Integer, nullable=False)
    total_mm_wasted = Column(Integer, nullable=True)
    last_updated = Column(DateTime, nullable=False)

    def __init__(self, num_print_success, mm_used, num_failed_print, total_mm_wasted, last_updated):
        """ Initializes a processing statistics objet """
        self.num_print_success = num_print_success
        self.mm_used = mm_used
        self.num_failed_print = num_failed_print
        self.total_mm_wasted = total_mm_wasted
        self.last_updated = last_updated

    def to_dict(self):
        """ Dictionary Representation of a statistics """
        dict = {}
        dict['num_print_success'] = self.num_print_success
        dict['mm_used'] = self.mm_used
        dict['num_failed_print'] = self.num_failed_print
        dict['total_mm_wasted'] = self.total_mm_wasted
        dict['last_updated'] = self.last_updated.strftime("%Y-%m-%dT%H:%M:%S.00%f")
        return dict
