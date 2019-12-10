import logging, re

from scrapper.enums.tasks import TaskKeys
from scrapper.enums.results import ResultKeys

logger = logging.getLogger(__name__)

class Results():
    def __init__(self, results, database, mail, settings):
        self.__results = results
        self.__database = database
        self.__mail = mail
        self.__settings = settings

    def save(self):
        self.__database.append_results(self.__results)

    def exclude_by_keywords(self, keywords):
        logger.debug("Excluding results by keywords.")
        filtered_results = []
        previous_results_count = len(self.__results)
        for result in self.__results:
            if not self.__are_keywords_in_result(result, keywords):
                filtered_results.append(result)
        self.__results = filtered_results
        next_results_count = len(self.__results)
        logger.info(f"{next_results_count}/{previous_results_count} left due to filtering.")

    def include_by_keywords(self, keywords):
        logger.debug("Including results by keywords.")
        filtered_results = []
        previous_results_count = len(self.__results)
        for result in self.__results:
            if self.__are_keywords_in_result(result, keywords):
                filtered_results.append(result)
        self.__results = filtered_results
        next_results_count = len(self.__results)
        logger.info(f"{next_results_count}/{previous_results_count} left due to filtering.")

    def __are_keywords_in_result(self, result, keywords):
        for keyword in keywords:
            if self.__is_keyword_in_result(result, keyword):
                return True
        return False

    def __is_keyword_in_result(self, result, keyword):
        for result_key in ResultKeys:
            try:
                if re.search(r"\b{}\b".format(keyword), result[result_key.name]) is not None:
                    return True
            except KeyError:
                continue
            except TypeError:
                continue

        return False

    def check_count(self, expected_results_count):
        logger.debug("Checking if there is enough results.")
        results_count = len(self.__results)
        if results_count < expected_results_count:
            logger.warning(f"Got {results_count} results. Expected at least {expected_results_count} results.")
            if self.__settings.notify_by_mail():
                self.__mail.warn_about_results(self.__task_dict[TaskKeys.scrapping_link.name], results_count, expected_results_count)
        logger.info(f"Got {results_count} results. Expected at least {expected_results_count} results.")