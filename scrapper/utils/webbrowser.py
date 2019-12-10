import logging

from selenium import webdriver
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException
from selenium.webdriver.firefox.options import Options

logger = logging.getLogger(__name__)

class WebBrowser():
    web_driver = None

    def __init__(self, headless=True):
        self.start_web_driver(headless)

    def set_web_driver(self, web_driver):
        self.web_driver = web_driver

    def reset_proxy(self):
        self.set_proxy("")

    def set_proxy(self, proxy_address):
        logger.debug(f"Setting proxy to {proxy_address}...")
        if proxy_address:
            host, port = proxy_address.split(":")
        else:
            host = ""
            port = ""
        self.open_new_tab()
        self.load_web_page("about:config")

        proxy_setting_script = f"""var prefs = Components.classes["@mozilla.org/preferences-service;1"]
                                    .getService(Components.interfaces.nsIPrefBranch);

                                    prefs.setIntPref("network.proxy.type", 1);
                                    prefs.setCharPref("network.proxy.http", "{host}");
                                    prefs.setIntPref("network.proxy.http_port", "{port}");
                                    prefs.setCharPref("network.proxy.ssl", "{host}");
                                    prefs.setIntPref("network.proxy.ssl_port", "{port}");
                                    prefs.setCharPref("network.proxy.ftp", "{host}");
                                    prefs.setIntPref("network.proxy.ftp_port", "{port}");"""
        self.web_driver.execute_script(proxy_setting_script)
        self.close_tab_by_number(1)


    def open_new_tab(self):
        logger.debug("Openning new tab in web browser...")
        self.web_driver.execute_script("window.open('');")
        tabs_count = self.tabs_count()
        self.switch_to_tab_by_number(tabs_count-1)

    def close_tab_by_number(self, tab_number):
        logger.debug(f"Closing tab {tab_number} in web browser...")
        tabs_count = self.tabs_count()
        self.switch_to_tab_by_number(tab_number)
        self.web_driver.close()
        if tabs_count > 1:
            self.switch_to_tab_by_number(0)

    def tabs_count(self):
        return len(self.web_driver.window_handles)

    def switch_to_tab_by_number(self, tab_number):
        logger.debug(f"Switching to tab {tab_number} in web browser...")
        self.web_driver.switch_to_window(self.web_driver.window_handles[tab_number])


    def start_web_driver(self, headless=True):
        if not self.is_web_driver_alive():
            logger.debug("Starting web driver...")
            options = Options()
            options.headless = headless

            self.web_driver = webdriver.Firefox(timeout=120, options=options, log_path="/var/tmp/geckodriver.log")
            logger.info("Started web driver...")

    def is_web_driver_alive(self):
        is_driver_dead = True
        if hasattr(self, 'driver') and self.web_driver:
            try:
                self.web_driver.current_url
                is_driver_dead = False
            except InvalidSessionIdException:
                pass
            except WebDriverException:
                pass
        logger.debug("Web driver is {}.".format("dead" if is_driver_dead else "alive"))
        return not is_driver_dead

    def load_web_page(self, web_page_url):
        if self.web_driver.current_url != web_page_url:
            logger.info(f"Loading {web_page_url}...")
            self.web_driver.get(web_page_url)

    def add_cookies(self, cookies):
        logger.debug(f"Adding {len(cookies)} cookies...")
        for cookie in cookies:
            self.web_driver.add_cookie(cookie)
        self.web_driver.execute_script("location.reload()")
        logger.info(f"Added {len(cookies)} cookies...")

    def __del__(self):
        self.web_driver.close()