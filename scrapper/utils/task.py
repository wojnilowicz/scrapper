import logging
from datetime import datetime
from datetime import timedelta

from scrapper.crawler.factory import crawler_by_scrapping_link
from scrapper.enums.tasks import TaskKeys
from scrapper.exceptions.exceptions import CaptchaEncountered

logger = logging.getLogger(__name__)

class Task():

    def __init__(self, task_dict, database, web_browser, mail, proxies, settings):
        self.__task_dict = task_dict
        self.__mail = mail
        self.__proxies = proxies
        self.__settings = settings
        self.__web_browser = web_browser
        self.__database = database
        self.__results = []

    def run(self):
        max_tries = 5
        for try_no in range(max_tries):
            if self.__settings.use_proxy():
                self.__web_browser.set_proxy(self.__proxies.next_valid_proxy())

            try:
                crawler = crawler_by_scrapping_link(self.__web_browser, self.__task_dict[TaskKeys.scrapping_link.name])
                self.__results = crawler.run_task(self.__task_dict)
            except CaptchaEncountered:
                if self.__settings.use_proxy():
                    logger.warning(f"Encountered captcha, try {try_no}. Continuing...")
                    continue
                raise
            except Exception:
                logger.exception(f"Task by number {self.__task_dict[TaskKeys.task_number.name]} met unresolvable error.")
                if self.__settings.notify_by_mail():
                    self.__mail.send_log()
                raise
            break

    def set_new_due_time(self):
        task_number = self.__task_dict[TaskKeys.task_number.name]
        logger.debug(f"Setting new due time for task by number {task_number}...")
        current_due_time = self.__task_dict[TaskKeys.scrapping_datetime.name]
        scrapping_period_in_hours = self.__task_dict[TaskKeys.scrapping_period_in_hours.name]
        new_due_time = datetime.now() #+ timedelta(hours = scrapping_period_in_hours)
        self.__database.write_attribute_of_task(task_number, TaskKeys.scrapping_datetime.name, new_due_time)
        logger.debug(f"Set new due time {self.__database.format_date_for_mysql(new_due_time)} " \
                     f"from old {self.__database.format_date_for_mysql(current_due_time)} " \
                     f"on task by number {task_number}.")

    def results(self):
        return self.__results

    def keywords_list(self):
        return self.__task_dict[TaskKeys.search_keywords.name].split(';')

    def minimal_results_count(self):
        return self.__task_dict[TaskKeys.minimal_results_count.name]