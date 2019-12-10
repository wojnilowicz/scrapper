import os, yaml
from logging.config import dictConfig

class Settings:
    @classmethod
    def notify_by_mail(cls):
        return cls.__read_general_settings()["notify_by_mail"]

    @classmethod
    def use_proxy(cls):
        return cls.__read_general_settings()["use_proxy"]

    @classmethod
    def download_proxy_list(cls):
        return cls.__read_general_settings()["download_proxy_list"]

    @classmethod
    def prune_invalid_proxies(cls):
        return cls.__read_general_settings()["prune_invalid_proxies"]

    @classmethod
    def tasks_from_yaml(cls):
        return cls.__read_general_settings()["tasks_from_yaml"]

    @classmethod
    def headless_web_browser(cls):
        return cls.__read_general_settings()["headless_web_browser"]

    @classmethod
    def smtp(cls):
        return cls.__read_settings_from_yaml(os.path.join(cls.__configuration_directory(), "smtp.yaml"))

    @classmethod
    def proxy(cls):
        return cls.__read_settings_from_yaml(os.path.join(cls.__configuration_directory(), "proxy.yaml"))

    @classmethod
    def database(cls):
        return cls.__read_settings_from_yaml(os.path.join(cls.__configuration_directory(), "database.yaml"))

    @classmethod
    def setup_logging(cls):
        my_logging = cls.__read_settings_from_yaml(os.path.join(cls.__configuration_directory(), "logging.yaml"))
        dictConfig(my_logging)

    @classmethod
    def __configuration_directory(cls):
        return os.path.join(os.path.join(os.path.abspath(os.curdir), "scrapper", "config"))

    @classmethod
    def __read_general_settings(cls):
        return cls.__read_settings_from_yaml(os.path.join(cls.__configuration_directory(), "general.yaml"))

    @classmethod
    def __read_settings_from_yaml(cls, yaml_file_name):
        with open(yaml_file_name, 'r') as yaml_file_content:
            configuration_dict = yaml.safe_load(yaml_file_content)
        return configuration_dict