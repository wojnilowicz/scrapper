from enum import Enum, auto, unique

@unique
class TaskKeys(Enum):
    job_title = auto()
    task_number = auto()
    site_name = auto()
    search_keywords = auto()
    scrapping_link = auto()
    scrapping_period_in_hours = auto()
    scrapping_datetime = auto()
    minimal_results_count = auto()