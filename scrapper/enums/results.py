from enum import Enum, auto, unique

@unique
class ResultKeys(Enum):
    result_number = auto()
    job_title = auto()
    application_link = auto()
    company_name = auto()
    company_size = auto()
    company_website = auto()