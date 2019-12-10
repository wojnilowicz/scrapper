import logging
from scrapper.crawler.glassdoor import Glassdoor

logger = logging.getLogger(__name__)

crawler_objects = {}

crawler_constructors = {
        "www.glassdoor.com": Glassdoor
        }

def crawler_by_scrapping_link(web_browser, scrapping_link):
    global crawler_objects
    global crawler_constructors

    is_crawler_id_found = False
    for crawler_id, crawler_constructor  in crawler_constructors.items():
        if crawler_id in scrapping_link:
            if crawler_id not in crawler_objects:
                crawler_objects[crawler_id] = crawler_constructor(web_browser)
                logger.debug(f"Selected crawler by id '{crawler_id}'")
            is_crawler_id_found = True
            break

    if not is_crawler_id_found:
        raise ValueError(f"{scrapping_link} is not supported by available crawlers.")

    return crawler_objects[crawler_id]