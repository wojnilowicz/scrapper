import time, re, os, logging
from collections import OrderedDict

from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By

from scrapper.utils.resources import Resources
from scrapper.enums.results import ResultKeys
from scrapper.enums.tasks import TaskKeys

from scrapper.exceptions.exceptions import CaptchaEncountered

logger = logging.getLogger(__name__)


def get_text_excluding_children(driver, element):
    return driver.execute_script(""" return jQuery(arguments[0]).contents().filter(function() {
    return this.nodeType == Node.TEXT_NODE; }).text();
    """, element)


class Glassdoor():
    web_browser = None
    web_driver = None
    web_page = "https://www.glassdoor.com"

    def __init__(self, web_browser):
        self.web_browser = web_browser
        self.web_driver = self.web_browser.web_driver

    def run_task(self, task_dict):
        if not self.is_logged_in():
            self.web_browser.load_web_page(self.web_page)
            cookies_path = os.path.join(os.path.abspath(os.curdir), "scrapper", "resources", "cookies", "glassdoor.json")
            cookies = Resources.read_cookies_from_json(cookies_path)
            self.web_browser.add_cookies(cookies)
            self.accept_cookies()
        self.web_browser.load_web_page(task_dict[TaskKeys.scrapping_link.name])
        self.check_captcha_presence()
        return self.scrape_results()

    def accept_cookies(self):
        wait = WebDriverWait(self.web_driver, 5)
        try:
            accept_cookies_button = wait.until(ec.visibility_of_element_located((By.ID,"_evidon-accept-button")))
        except TimeoutException:
            logger.debug("Accept cookies button not found.")
        else:
            accept_cookies_button.click()

    def is_logged_in(self):
        try:
            self.web_driver.find_element_by_css_selector("li[class~=signed-in]")
        except NoSuchElementException:
            return False
        else:
            return True

    def search_by_keywords(self):
        keyword_field = self.web_driver.find_element_by_id("sc.keyword")
        search_button = self.web_driver.find_element_by_id("HeroSearchButton")
        keyword_field.send_keys(Keys.CONTROL,"a",Keys.DELETE);
        keyword_field.send_keys("Software Developer")
        search_button.click()

    def scrape_results(self):
        results = []

        result_pages_count = self.scrape_result_pages_count()
        if not result_pages_count:
            logger.info("No results found.")
            return results

        max_results_to_scrape = 10
        max_result_pages_to_scrape = 2
        starting_result_page_number = 1

        max_consecutive_failed_results_to_break = 3
        consecutive_failed_results_count  = 0

        current_result_number = 0
        total_results_count = 0
        current_result_page_number = starting_result_page_number - 1
        while current_result_page_number < result_pages_count:
            current_result_page_number += 1
            if current_result_page_number > max_result_pages_to_scrape:
                break

            self.go_to_result_page_number(current_result_page_number)
            logger.debug(f"Scrapping result page {current_result_page_number}/{result_pages_count}...")

            new_results = self.web_driver.find_elements_by_css_selector(".jlGrid>.jl")
            new_results_count = len(new_results)
            total_results_count += new_results_count
            logger.debug(f"Got {new_results_count} new offers.")

            is_enought_results_gathered = False
            for new_result in new_results:
                current_result_number += 1
                if current_result_number > max_results_to_scrape:
                    is_enought_results_gathered = True
                    break

                logger.debug(f"Scrapping result {current_result_number}/{total_results_count}...")
                try:
                    results.append(self.scrape_result(new_result))
                except Exception:
                    consecutive_failed_results_count += 1
                    if consecutive_failed_results_count > max_consecutive_failed_results_to_break:
                        logger.warning(f"Failed to scrape {max_consecutive_failed_results_to_break} results in a row, so breaking.")
                        if len(results) > 0:
                            return results
                        raise
                    else:
                        logger.warning(f"Failed to scrape {current_result_number}/{total_results_count} but continuing.")
                        continue
                consecutive_failed_results_count = 0

            if is_enought_results_gathered:
                break

        return results

    def scrape_result(self, offer_entry):
        result = {}
        self.ensure_offer_is_visible(offer_entry)

        scrapping_functions = OrderedDict([
            (ResultKeys.job_title.name, self.scrape_job_title),
            (ResultKeys.company_name.name, self.scrape_company_name),
            (ResultKeys.application_link.name, self.scrape_application_link),
            (ResultKeys.company_size.name, self.scrape_company_size),
            (ResultKeys.company_website.name, self.scrape_company_website)
            ])

        max_try_again_attempts = 3
        try_again_attempt = 0
        for key, value in scrapping_functions.items():
            while key not in result:
                try:
                    result[key] = value(offer_entry)
                except ElementClickInterceptedException as e:
                    if not self.is_modal_dialog_opened():
                        try_again_attempt += 1
                        if try_again_attempt > max_try_again_attempts:
                            raise
                        seconds_to_try_again = 5
                        logger.warning(f"{key} is obscured by some other element." \
                                       "The error is:\n" + e.msg + f"\nDelaying another try by {seconds_to_try_again} seconds.")
                        time.sleep(seconds_to_try_again)
        return result

    def scrape_job_title(self, offer_entry):
        employer_name_text = offer_entry.find_element_by_css_selector("div[class=jobContainer]>a[class~=jobLink]")
        return employer_name_text.text

    def scrape_application_link(self, offer_entry):
        possible_button_variants = OrderedDict ([
                ("div[class~=applyCTA]>a", "href"),
                ("div[class~=applyCTA]>button", "data-job-url"),
                ])

        for key, value in possible_button_variants.items():
            try:
                apply_now_button = self.web_driver.find_element_by_css_selector(key)
            except NoSuchElementException:
                pass
            else:
                return apply_now_button.get_attribute(value)

    def scrape_authors_data(self, offer_entry):
        pass

    def scrape_company_name(self, offer_entry):
        company_name_text = offer_entry.find_element_by_css_selector(".jobEmpolyerName")
        return company_name_text.text

    def scrape_company_size(self, offer_entry):
        if not self.go_to_tab_name("Company"):
            return None
        size_text = self.web_driver.find_element_by_xpath("//label[text()='Size']/../span")

        return size_text.text

    def scrape_company_website(self, offer_entry):
        if not self.go_to_tab_name("Company"):
            return None
        try:
            company_website_text = offer_entry.find_element_by_xpath("//span[contains(@class,'website')]/a")
        except NoSuchElementException:
            logger.warning("No website information available.")
        else:
            return company_website_text.get_attribute("href")

    def go_to_tab_name(self, tab_name):
        try:
            tab = self.web_driver.find_element_by_xpath(f"//div[@data-tab-type]/span[text()='{tab_name}']")
        except NoSuchElementException:
            logger.warning(f"No tab named '{tab_name}' available.")
            return False
        else:
            tab.click()
            return True

    def scrape_result_pages_count(self):
        result = self.__scrape_page_numbering()
        return result['pages_count']

    def scrape_current_result_page_number(self):
        result = self.__scrape_page_numbering()
        return result['page_number']

    def __scrape_page_numbering(self):
        result = {"page_number": 0, "pages_count": 0}
        try:
            page_numbering = self.web_driver.find_element_by_css_selector(f"div[id=ResultsFooter]>div[class~=hideMob]")
        except NoSuchElementException:
            logger.error("Cannot find results page numbering.")
            return result
        p = re.compile("\D*(?P<page_number>\d+)\D*(?P<pages_count>\d+)\D*")
        m = p.search(page_numbering.text)
        try:
            result["page_number"] = int(m.group('page_number'))
            result["pages_count"] = int(m.group('pages_count'))
        except AttributeError:
            logger.warning("Cannot scrape result pages numbering.")
        return result

    def go_to_result_page_number(self, requested_page_number):
        current_page_number = self.scrape_current_result_page_number()
        while requested_page_number != current_page_number:
            logger.debug(f"We are on page {current_page_number} but we want to be on page {requested_page_number}.")
            some_page_button = self.web_driver.find_element_by_css_selector("div.pagingControls li.page a")
            some_page_link = some_page_button.get_attribute("href")
            p = re.compile(".*IP(?P<page_number>\d+).htm.*")
            m = p.search(some_page_link)
            try:
                requested_page_link = some_page_link.replace("IP{}.htm".format(m.group("page_number")), "IP{}.htm".format(requested_page_number))
            except AttributeError:
                logger.debug(f"Absolute navigation failed, so try relative navigation.")
                if current_page_number > requested_page_number:
                    self.switch_to_prev_results_page()
                else:
                    self.switch_to_next_results_page()
            else:
                self.web_browser.load_web_page(requested_page_link)

            current_page_number = self.scrape_current_result_page_number()


    def switch_to_next_results_page(self):
        next_page_button = self.web_driver.find_element_by_css_selector("div.pagingControls li.next a")
        next_page_button.click()

    def switch_to_prev_results_page(self):
        prev_page_button = self.web_driver.find_element_by_css_selector("div.pagingControls li.prev a")
        prev_page_button.click()

    def is_modal_dialog_opened(self, close_modal_dialog=True):
        logger.info("Checking if modal dialog is opened...")
        try:
            modal_dialog_close_button = self.web_driver.find_element_by_css_selector(".modal_closeIcon")
        except NoSuchElementException:
            logger.info("Modal dialog isn't opened.")
            return False
        else:
            log_message = "Modal dialog is opened."
            if close_modal_dialog:
                logger.info(log_message + " Closing it...")
                modal_dialog_close_button.click()
            else:
                logger.info(log_message + " Left opened.")
                pass
            return True

    def check_captcha_presence(self):
        logger.info("Checking if captcha is present...")
        try:
            self.web_driver.find_element_by_id("recaptcha_submit")
        except NoSuchElementException:
            logger.info("Captcha isn't present.")
            return
        else:
            logger.info("Captcha is present.")
            raise CaptchaEncountered

    def ensure_offer_is_visible(self, offer_entry):
        selected_offer_entry = self.web_driver.find_element_by_css_selector(".jlGrid .jl.selected")
        if selected_offer_entry != offer_entry:
            job_tab_css_selector = "div[data-tab-type='job']"
            job_tab = self.web_driver.find_element_by_css_selector(job_tab_css_selector)
            offer_entry.click()
            wait = WebDriverWait(self.web_driver, 10)

            try:
                wait.until(ec.staleness_of(job_tab))
            except TimeoutException:
                logger.warning("Previous job tab doesn't disappear.")
            else:
                try:
                    wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, job_tab_css_selector)))
                except TimeoutException:
                    logger.warning("New job tab doesn't appear.")
