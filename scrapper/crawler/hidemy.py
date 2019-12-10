import logging

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By


logger = logging.getLogger(__name__)

class HideMy():
    web_browser = None
    web_driver = None
    web_page = "https://hidemy.name/en/"

    def __init__(self, web_browser):
        self.web_browser = web_browser
        self.web_driver = self.web_browser.web_driver

    def scrape_proxies(self, proxy_url="https://hidemy.name/en/proxy-list/?maxtime=1000&type=h&anon=234#list"):
        proxies = []
        self.web_browser.load_web_page("about:preferences")
        self.web_browser.load_web_page(proxy_url)

        wait = WebDriverWait(self.web_driver, 10)
        try:
            wait.until(ec.visibility_of_element_located((By.CLASS_NAME,"button_green")))
        except TimeoutException:
            logger.error("Table with proxies not found.")
            return proxies

        while True:
            page_proxies = self.scrape_proxies_page()
            proxies += page_proxies
            if not self.switch_to_next_results_page():
                break

        proxies_count = len(proxies)
        if not proxies_count:
            logger.error(f"No proxies for {proxy_url}.")
        else:
            logger.info(f"Found {proxies_count} proxies for {proxy_url}.")

        return proxies

    def switch_to_next_results_page(self):
        try:
            next_page_button = self.web_driver.find_element_by_css_selector("div[class=proxy__pagination] li[class=arrow__right] a")
        except NoSuchElementException:
            return False
        next_page_button.click()
        return True

    def scrape_proxies_page(self):
        proxies = []
        ip_addresses = self.web_driver.find_elements_by_css_selector("td[class=tdl]")
        ip_addresses_count = len(ip_addresses)
        if not ip_addresses_count:
            return proxies

        ports = self.web_driver.find_elements_by_css_selector("tr>td:nth-of-type(2)")
        ports_count = len(ports)

        if ip_addresses_count != ports_count:
            logger.error(f"IP addresses count {ip_addresses_count} is not equal to ports count {ports_count}.")
            return proxies
        for i in range(ip_addresses_count):
            proxy = f"{ip_addresses[i].text}:{ports[i].text}"
            proxies.append(proxy)
        return proxies

