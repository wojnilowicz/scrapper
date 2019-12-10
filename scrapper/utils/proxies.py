import logging, requests, signal, os

from scrapper.crawler.hidemy import HideMy
from selenium.common.exceptions import NoSuchElementException

logger = logging.getLogger(__name__)


class Proxies():
    def __init__(self, web_browser, proxies_filename=None):
        signal.signal(signal.SIGALRM, self.__handler)
        self.__web_browser = web_browser
        self.__web_driver = web_browser.web_driver
        self.current_proxy_index = 0
        self.__proxies_filename = proxies_filename
        if not self.__proxies_filename:
            self.__proxies_filename = os.path.join(os.path.join(os.path.abspath(os.curdir),\
                                                "scrapper",\
                                                "resources",\
                                                "proxies.txt"))
        self.__proxies = self.__read_proxies()

    def next_valid_proxy(self, proxy_timeout_in_seconds = 3):
        if not self.__is_my_api_website_alive():
            logger.warning("Empty proxy returned.")
            return ''

        while True:
            proxy = self.__next_proxy()
            if not proxy or self.__is_proxy_valid(proxy, proxy_timeout_in_seconds):
                break
            self.__proxies.remove(proxy)

        if not proxy:
            logger.warning("Empty proxy returned.")

        return proxy

    def __next_proxy(self):
        proxies_count = len(self.__proxies)
        if proxies_count == 0:
            logger.warning("No proxies available.")
            self.current_proxy_index = 0
            return ''

        elif proxies_count == 1:
            logger.warning("Only one proxy left, so no proxy rotation.")

        next_proxy_index = self.current_proxy_index + 1

        if next_proxy_index >= proxies_count:
            next_proxy_index = 0
        self.current_proxy_index = next_proxy_index
        return self.__proxies[self.current_proxy_index]

    def download_new_proxies(self, proxy_url="https://hidemy.name/en/proxy-list/?maxtime=5000&type=h&anon=234#list"):
        logger.debug(f"Starting to download new proxies from {proxy_url}...")
        proxy_provider = HideMy(self.__web_browser)
        proxies = proxy_provider.scrape_proxies(proxy_url)
        logger.info(f"Downloaded {len(proxies)} proxies.")
        self.__update_proxies(proxies)
        self.__proxies = proxies

    def prune_invalid_proxies(self, proxy_timeout_in_seconds = 2):
        logger.debug("Validating proxies...")
        filtered_proxies = self.__filter_out_invalid_proxies(self.__proxies, proxy_timeout_in_seconds)
        self.__write_proxies(filtered_proxies)
        original_proxies_count = len(self.__proxies)
        filtered_proxies_count = len(filtered_proxies)
        self.__proxies = filtered_proxies
        logger.info(f"{filtered_proxies_count}/{original_proxies_count} proxies are valid.")

    def save(self):
        self.__write_proxies(self.__proxies)

    def __update_proxies(self, proxies_list):
        proxies_in_txt = self.__read_proxies()
        proxies_to_write = self.__filter_out_duplicated_proxies(proxies_list + proxies_in_txt)
        new_proxies_count = len(proxies_to_write) - len(proxies_in_txt)
        self.__write_proxies(proxies_to_write)
        logger.info(f"Updated with {new_proxies_count} new proxies.")

    def __write_proxies(self, proxies_list):
        logger.debug(f"Writting {len(proxies_list)} proxies...")

        with open(self.__proxies_filename, "w") as txt_file:
            txt_file.writelines('\n'.join(proxies_list) + '\n')
            logger.info(f"Wrote {len(proxies_list)} proxies.")

    def __read_proxies(self):
        logger.debug("Reading proxies.")

        with open(self.__proxies_filename, "r") as txt_file:
            proxies = txt_file.read().splitlines()

        logger.info(f"Read {len(proxies)} proxies.")
        return proxies

    def __filter_out_duplicated_proxies(self, unfiltered_proxies):
        filtered_proxies = []
        for i in unfiltered_proxies:
          if i not in filtered_proxies:
            filtered_proxies.append(i)
        return filtered_proxies

    def __handler(self, signum, frame):
        raise Exception()

    def __filter_out_invalid_proxies(self, all_proxies, proxy_timeout_in_seconds = 5):
        if not self.__is_my_api_website_alive():
            logger.error("www.myip.com is down and cannot filter out proxies.")
            raise Exception()

        all_proxies = self.__filter_out_duplicated_proxies(all_proxies)
        all_proxies_count = len(all_proxies)
        working_proxies = []

        logger.debug(f"Checking {all_proxies_count} proxies...")

        proxy_index = 0
        for proxy in all_proxies:
            proxy_index += 1
            is_proxy_valid = self.__is_proxy_valid(proxy, proxy_timeout_in_seconds)
            if is_proxy_valid:
                working_proxies.append(proxy)
            proxy_of_proxies = f"{proxy_index}/{all_proxies_count}"
            logger.debug(f"Proxy {proxy:{21}} which is {proxy_of_proxies:{7}} is {'valid' if is_proxy_valid else 'invalid'}.")

        return working_proxies

    def __is_proxy_valid(self, proxy, proxy_timeout_in_seconds=2):
        if not proxy:
            return False

        request_proxies = {"http": proxy, "https": proxy}
        signal.alarm(proxy_timeout_in_seconds)
        is_proxy_valid = True
        try:
            request_response = requests.get("https://api.myip.com", proxies=request_proxies)
        except Exception:
            is_proxy_valid = False
        finally:
            signal.alarm(0)

        if is_proxy_valid and request_response.status_code != requests.codes.ok:
            is_proxy_valid = False

        if is_proxy_valid and self.__is_error_page_open():
            is_proxy_valid = False

        return is_proxy_valid

    def __is_error_page_open(self):
        try:
            self.__web_driver.find_element_by_id("errorPageContainer")
        except NoSuchElementException:
            return False
        else:
            return True

    def __is_my_api_website_alive(self):
        is_my_api_website_alive = True
        try:
            request_response = requests.get("https://api.myip.com")
        except Exception:
            is_my_api_website_alive = False

        if is_my_api_website_alive and request_response.status_code != requests.codes.ok:
            is_my_api_website_alive = False
        if not is_my_api_website_alive:
            logger.warning("www.myip.com is down.")
        return is_my_api_website_alive