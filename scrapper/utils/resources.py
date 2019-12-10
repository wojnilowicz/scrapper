import yaml, os, logging
from collections import OrderedDict
from scrapper.enums.tasks import TaskKeys
from scrapper.utils.readers.json.cookies import cookies_from_json

logger = logging.getLogger(__name__)

class Resources:
    @classmethod
    def read_tasks(cls, yaml_file_name = None):
        if not yaml_file_name:
            yaml_file_name = os.path.join(cls.__resources_directory(), "tasks.yaml")
        if not os.path.exists(yaml_file_name):
            logger.warning(f"No yaml file with tasks at {yaml_file_name}.")
            cls.__write_example_task_to_yaml(yaml_file_name)
            return

        with open(yaml_file_name, "r") as yaml_file:
            yaml_file_content = yaml.safe_load(yaml_file)

        tasks_list = []
        for task_name, task_dict in yaml_file_content[0].items():
            tasks_list.append(task_dict)
        logger.info(f"Found {len(tasks_list)} tasks in yaml file.")
        return tasks_list

    @classmethod
    def __write_example_task(cls, yaml_file_name):
        example_task = [{"example_task" : OrderedDict([
        (TaskKeys.site_name.name, "example.com"),
        (TaskKeys.search_keywords.name, "First keyword,Second keyword"),
        (TaskKeys.scrapping_link.name, "https://www.example.com/job"),
        (TaskKeys.scrapping_period_in_hours.name, 1),
        ])}]

        example_task = [{"example_task" : OrderedDict([
        (TaskKeys.site_name.name, "glassdoor.com"),
        (TaskKeys.search_keywords.name, "Software Engineer"),
        (TaskKeys.scrapping_link.name, "https://www.glassdoor.com/Job/jobs.htm?suggestCount=0&suggestChosen=true&clickSource=searchBtn&typedKeyword=Soft&sc.keyword=Software+Engineer&locT=C&locId=2970449&jobType="),
        (TaskKeys.scrapping_period_in_hours.name, 1),
        ])}]

        logger.info(f"Creating yaml file with example task at {yaml_file_name}.")
        with open(yaml_file_name, "w") as yaml_file:
            yaml.add_representer(OrderedDict, lambda dumper, data: dumper.represent_mapping('tag:yaml.org,2002:map', data.items()))
            yaml.dump(example_task, yaml_file)
        pass

    @classmethod
    def read_cookies_from_json(cls, json_file_name):
        return cookies_from_json(json_file_name)

    @classmethod
    def __resources_directory(cls):
        return os.path.join(os.path.join(os.path.abspath(os.curdir), "scrapper", "resources"))