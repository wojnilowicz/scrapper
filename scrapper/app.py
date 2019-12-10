import logging

from scrapper.storage.database import Database
from scrapper.utils.webbrowser_singleton import get_web_browser_instance
from scrapper.utils.mail import Mail
from scrapper.utils.task import Task
from scrapper.utils.results import Results
from scrapper.utils.settings import Settings
from scrapper.utils.resources import Resources
from scrapper.utils.proxies import Proxies
from scrapper.utils.processes import ensure_web_browser_is_not_running, is_another_scrapper_instance_present

logger = logging.getLogger(__name__)

def run():
    if is_another_scrapper_instance_present():
        return
    ensure_web_browser_is_not_running()

    try:
        run_unguarded()
    except Exception:
        logger.exception("Application met unresolvable error.")
        if Settings.notify_by_mail():
            my_mail = Mail(Settings.smtp())
            my_mail.send_log()

def run_unguarded():
    my_settings = Settings()
    my_settings.setup_logging()

    my_database = Database(Settings.database())

    my_mail = None
    if my_settings.notify_by_mail():
        my_mail = Mail(Settings.smtp())

    if my_settings.tasks_from_yaml():
        my_task_list = Resources.read_tasks()
        my_database.append_tasks(my_task_list)

    my_web_browser = get_web_browser_instance(my_settings.headless_web_browser())

    my_proxies = None
    if my_settings.use_proxy():
        my_proxies = Proxies(my_web_browser)
        if my_settings.download_proxy_list():
            my_proxies.download_new_proxies(my_settings.proxy()["address"])
        if my_settings.prune_invalid_proxies():
            my_proxies.prune_invalid_proxies()

    my_task_list = my_database.due_tasks()
    for my_task_dict in my_task_list:
        my_task_object = Task(task_dict=my_task_dict,
                              database=my_database,
                              web_browser=my_web_browser,
                              mail=my_mail,
                              proxies=my_proxies,
                              settings=my_settings)

        try:
            my_task_object.run()
        except Exception:
            raise

        my_results_object = Results(results=my_task_object.results(),
                              database=my_database,
                              mail=my_mail,
                              settings=my_settings)

        my_results_object.exclude_by_keywords(my_task_object.keywords_list())
        my_results_object.check_count(my_task_object.minimal_results_count())
        my_results_object.save()
        my_task_object.set_new_due_time()
    if my_proxies:
        my_proxies.save()
    if my_database:
        del my_database