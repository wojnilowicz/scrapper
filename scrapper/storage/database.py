import logging
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
from datetime import timedelta

from scrapper.enums.tasks import TaskKeys
from scrapper.enums.results import ResultKeys


logger = logging.getLogger(__name__)


class Database:
    my_database_connection: mysql.connector.MySQLConnection = None
    my_database_cursor: mysql.connector.cursor.MySQLCursor = None
    my_task_table_name = "tasks"
    my_results_table_name = "results"

    def __init__(self, config_dict):
        self.connect_to_server(config_dict["host"], config_dict["user"], config_dict["password"])
        my_database_name = config_dict["database_name"]
        if not self.is_database_created(my_database_name):
            self.create_database(my_database_name)
        self.my_database_connection.database = my_database_name

        self.create_tasks_table()
        self.create_results_table()

    def connect_to_server(self, host, user, password):
        logger.debug("Connecting to MySQL server...")
        try:
            self.my_database_connection = mysql.connector.connect(host=host, user=user, password=password)
        except mysql.connector.errors.ProgrammingError as err:
            logger.error(err)
            raise
        except mysql.connector.errors.InterfaceError as err:
            logger.error(err)
            raise
        else:
            logger.info("Connected to MySQL server.")

        self.my_database_cursor = self.my_database_connection.cursor()

    def recreate_tables(self):
        self.delete_table(self.my_task_table_name)
        self.delete_table(self.my_results_table_name)
        self.create_tasks_table()
        self.create_results_table()

    def append_result(self, result_dict):
        self.append_results([result_dict])

    def append_results(self, results_list):
        self.append_records(results_list, self.my_results_table_name)

    def append_record(self, records_dict, table_name):
        self.append_records([records_dict], table_name)

    def append_records(self, records_list, table_name, update_records=True):
        records_to_append_count = len(records_list)
        if records_to_append_count == 0:
            logger.debug("No records to append.")
            return
        logger.debug(f"Appending {records_to_append_count} records to table '{table_name}'...")

        value_names = ""
        value_placeholders = ""
        value_replacements = ""

        for record_key in records_list[0]:
            value_names += f"{record_key},"
            value_placeholders += f"%({record_key})s,"
            value_replacements += f"{record_key}=VALUES({record_key}),"

        if not update_records:
            record_key = self.primary_key_name(table_name)
            value_replacements = f"{record_key}=VALUES({record_key}),"

        value_names = value_names.rstrip(',')
        value_placeholders = value_placeholders.rstrip(',')
        value_replacements = value_replacements.rstrip(',')

        sql_query = f"INSERT INTO {table_name} " \
                    f"({value_names}) " \
                    f"VALUES ({value_placeholders}) " \
                    f"ON DUPLICATE KEY UPDATE {value_replacements};"

        records_before_appending_count = self.records_count(table_name)
        self.my_database_cursor.executemany(sql_query, records_list)
        self.my_database_connection.commit()
        records_after_appending_count = self.records_count(table_name)
        records_appended_count = records_after_appending_count - records_before_appending_count
        records_updated_count = records_to_append_count - records_appended_count

        if records_updated_count:
            logger.info("Appended {} from {} records and the rest has been {}.".format(records_appended_count, records_to_append_count, "updated" if update_records else "skipped"  ))

    def primary_key_name(self, table_name):
        sql_query = f"SHOW KEYS FROM {table_name} WHERE Key_name = 'PRIMARY'"
        my_database_cursor = self.my_database_connection.cursor(named_tuple=True)
        my_database_cursor.execute(sql_query)

        for row in my_database_cursor:
            name_of_primary_key = row.Column_name
        my_database_cursor.close()
        return name_of_primary_key

    def records_count(self, table_name):
#        logger.debug(f"Checking records count for table named {table_name}...")
        sql_query = f"SELECT COUNT(*) FROM {table_name}"
        self.my_database_cursor.execute(sql_query)
        records_count = self.my_database_cursor.fetchone()[0]
        logger.debug(f"Records count for table named '{table_name}' is {records_count}.")
        return records_count

    def read_task(self, task_number):
        logger.info(f"Reading task number {task_number}...")
        tasks_count = self.records_count(self.my_task_table_name)
        if task_number > tasks_count:
            logger.error("Requested task number {} but maximum number is {}.".format(task_number, tasks_count))

        my_database_cursor = self.my_database_connection.cursor(dictionary=True)
        sql_query = f"SELECT *" \
                    f"FROM {self.my_task_table_name} " \
                    f"WHERE {TaskKeys.task_number.name}={task_number}"

        my_database_cursor.execute(sql_query)
        task_dict = my_database_cursor.fetchone()
        my_database_cursor.close()
        return task_dict

    def append_task(self, task_dict):
        self.append_tasks([task_dict])

    def append_tasks(self, tasks_list):
        self.append_records(tasks_list, self.my_task_table_name)

    def create_tasks_table(self):
        if self.is_table_created(self.my_task_table_name):
            return

        logger.debug(f"Creating table named '{self.my_task_table_name}'...")
        sql_query = f"CREATE TABLE {self.my_task_table_name} (" \
                    f"{TaskKeys.task_number.name} TINYINT UNSIGNED NOT NULL AUTO_INCREMENT, " \
                    f"{TaskKeys.site_name.name} VARCHAR(17) NOT NULL, " \
                    f"{TaskKeys.search_keywords.name} VARCHAR(100) NOT NULL, " \
                    f"{TaskKeys.scrapping_link.name} VARCHAR(255) NOT NULL, " \
                    f"{TaskKeys.scrapping_period_in_hours.name} SMALLINT UNSIGNED NOT NULL, " \
                    f"{TaskKeys.scrapping_datetime.name} DATETIME NULL, " \
                    f"{TaskKeys.minimal_results_count.name} TINYINT DEFAULT 0, " \
                    f"PRIMARY KEY ({TaskKeys.task_number.name}), " \
                    f"CONSTRAINT unique_task UNIQUE KEY (" \
                    f"{TaskKeys.search_keywords.name}, " \
                    f"{TaskKeys.scrapping_link.name} " \
                    ")" \
                    ");"
        self.my_database_cursor.execute(sql_query)
        logger.info(f"Created table named '{self.my_task_table_name}'.")

    def due_tasks(self):
        logger.debug(f"Preparing list of tasks due to scrapping...")
        tasks_list = []
        date_time = datetime.now()
        my_sql_date_time = date_time.strftime('%Y-%m-%d %H:%M:%S')
        sql_query = f"SELECT * " \
                    f"FROM {self.my_task_table_name} " \
                    f"WHERE {TaskKeys.scrapping_datetime.name}<='{my_sql_date_time}' " \
                    f"OR {TaskKeys.scrapping_datetime.name} IS NULL" \
                    ";"
        my_database_cursor = self.my_database_connection.cursor(dictionary=True)
        my_database_cursor.execute(sql_query)
        for row in my_database_cursor:
            tasks_list.append(row)
        my_database_cursor.close()
        logger.debug(f"Prepared list of {len(tasks_list)} tasks due to scrapping.")
        return tasks_list

    def set_new_due_time_on_task(self, task_number):
        logger.debug(f"Setting new due time for task by number {task_number}...")
        current_due_time = self.read_attribute_of_task(task_number, TaskKeys.scrapping_datetime.name)
        scrapping_period_in_hours = self.read_attribute_of_task(task_number, TaskKeys.scrapping_period_in_hours.name)
        new_due_time = datetime.now() #+ timedelta(hours = scrapping_period_in_hours)
        self.write_attribute_of_task(task_number, TaskKeys.scrapping_datetime.name, new_due_time)
        logger.debug(f"Set new due time {self.format_date_for_mysql(new_due_time)} " \
                     f"from old {self.format_date_for_mysql(current_due_time)} " \
                     f"on task by number {task_number}.")

    def write_date_time_on_task(self, task_number, date_time):
        logger.debug(f"Writing time stamp on task by number {task_number}...")
        my_sql_date_time = self.format_date_for_mysql(date_time)
        sql_query = f"UPDATE {self.my_task_table_name} " \
            f"SET {TaskKeys.scrapping_datetime.name}='{my_sql_date_time}' "\
            f"WHERE {TaskKeys.task_number.name}={task_number}" \
            ";"
        self.my_database_cursor.execute(sql_query)
        self.my_database_connection.commit()
        logger.debug(f"Wrote time stamp on task by number {task_number}.")

    def format_date_for_mysql(self, date_time):
        if date_time is None:
            return ''
        return date_time.strftime('%Y-%m-%d %H:%M:%S')

    def read_date_time_on_task(self, task_number):
        sql_query = f"SELECT {TaskKeys.scrapping_datetime.name} " \
                    f"FROM {self.my_task_table_name} "\
                    f"WHERE {TaskKeys.task_number.name}={task_number}" \
                    ";"
        self.my_database_cursor.execute(sql_query)
        return self.my_database_cursor.fetchone()[0]

    def write_attribute_of_task(self, task_number, attribute_name, attribute_value):
        logger.debug(f"Writing attribute by name '{attribute_name}' on task by number {task_number}...")
        date_attribute_names = [TaskKeys.scrapping_datetime.name]
        if attribute_name in date_attribute_names:
            attribute_value = attribute_value.strftime('%Y-%m-%d %H:%M:%S')
        sql_query = f"UPDATE {self.my_task_table_name} " \
            f"SET {attribute_name}='{attribute_value}' "\
            f"WHERE {TaskKeys.task_number.name}={task_number}" \
            ";"
        self.my_database_cursor.execute(sql_query)
        self.my_database_connection.commit()
        logger.info(f"Wrote attribute by name '{attribute_name}' on task by number {task_number}.")

    def read_attribute_of_task(self, task_number, attribute_name):
        sql_query = f"SELECT {attribute_name} " \
                    f"FROM {self.my_task_table_name} "\
                    f"WHERE {TaskKeys.task_number.name}={task_number}" \
                    ";"
        self.my_database_cursor.execute(sql_query)
        return self.my_database_cursor.fetchone()[0]

    def expected_results_count(self, task_number):
        expected_results_count = self.read_attribute_of_task \
            (task_number, TaskKeys.minimal_results_count.name)

        if not expected_results_count:
            expected_results_count = 0
        return expected_results_count

    def is_table_created(self, table_name):
        logger.debug(f"Checking if table named '{table_name}' exists...")
        try:
            self.my_database_cursor.execute(f"SELECT 1 FROM {table_name} LIMIT 1;")
        except mysql.connector.errors.ProgrammingError as err:
            if err.errno == errorcode.ER_NO_SUCH_TABLE:
                logger.debug(f"Table named '{table_name}' doesn't exist.")
            else:
                logger.error(err.msg)
                raise
            return False
        else:
            self.my_database_cursor.fetchall()
            logger.debug(f"Table named '{table_name}' exists.")
            return True

    def delete_table(self, table_name):
        logger.debug(f"Deleting table named '{table_name}'...")
        try:
            self.my_database_cursor.execute(f"DROP TABLE {table_name};")
            logger.info(f"Deleted table named '{table_name}'.")
        except mysql.connector.errors.ProgrammingError as err:
            if err.errno == errorcode.ER_BAD_TABLE_ERROR:
                logger.debug(f"Table named '{table_name}' doesn't exist.")
            else:
                logger.error(err.msg)
                raise

    def clear_table(self, table_name):
        if self.is_table_created(self.my_task_table_name):
            return
        self.my_database_cursor.execute("SELECT COUNT(*) FROM {};".format(table_name))
        row_count = self.my_database_cursor.fetchone()[0]
        if not row_count:
            return

        logger.info(f"Deleting {row_count} rows from table named '{table_name}'...")
        self.my_database_cursor.execute("TRUNCATE TABLE {};".format(table_name))
        self.my_database_cursor.execute("SELECT COUNT(*) FROM {};".format(table_name))
        row_count = self.my_database_cursor.fetchone()[0]
        if row_count:
            logger.error(f"Error: row count still at {row_count}")

    def create_results_table(self):
        if self.is_table_created(self.my_results_table_name):
            return

        logger.debug(f"Creating table named '{self.my_results_table_name}'...")
        sql_query = f"CREATE TABLE {self.my_results_table_name} (" \
                    f"{ResultKeys.result_number.name} INT UNSIGNED AUTO_INCREMENT, " \
                    f"{ResultKeys.job_title.name} VARCHAR(100) NOT NULL, " \
                    f"{ResultKeys.application_link.name} VARCHAR(255), " \
                    f"{ResultKeys.company_name.name} VARCHAR(100) NOT NULL, " \
                    f"{ResultKeys.company_size.name} VARCHAR(100), " \
                    f"{ResultKeys.company_website.name} VARCHAR(100), " \
                    f"PRIMARY KEY ({ResultKeys.result_number.name}), " \
                    f"CONSTRAINT unique_application UNIQUE KEY (" \
                    f"{ResultKeys.job_title.name}, " \
                    f"{ResultKeys.company_name.name} " \
                    ")" \
                    ");"
        self.my_database_cursor.execute(sql_query)
        logger.info(f"Created table named '{self.my_results_table_name}'.")

    def create_database(self, database_name):
        logger.debug(f"Creating database named '{database_name}'...")
        try:
            self.my_database_cursor.execute(f"CREATE DATABASE {database_name} CHARACTER SET utf8mb4;")
        except mysql.connector.errors.DatabaseError as err:
            if err.errno != errorcode.ER_DB_CREATE_EXISTS:
                logger.info(err.msg)
                raise
        else:
            logger.info(f"Database named '{database_name}' has been created.")


    def delete_database(self, database_name):
        logger.debug(f"Deleting database named '{database_name}'...")
        try:
            self.my_database_cursor.execute(f"DROP DATABASE {database_name};")
        except mysql.connector.errors.ProgrammingError as err:
            if err.errno != errorcode.ER_BAD_DB_ERROR:
                logger.error(err.msg)
                raise
        else:
            logger.info(f"Deleted database named '{database_name}'.")

    def is_database_created(self, database_name):
        logger.debug(f"Checking if database named '{database_name}' exists.")
        try:
            self.my_database_connection.database = database_name
        except mysql.connector.errors.ProgrammingError as err:
            if err.errno != errorcode.ER_BAD_DB_ERROR:
                logger.error(err.msg)
                raise
            else:
                logger.debug(f"Database named '{database_name}' doesn't exists.")
            return False
        else:
            logger.debug(f"Database named '{database_name}' exists.")
            return True


    def __del__(self):
        logger.debug("Disconnecting from MySQL server...")
        if not self.my_database_connection is None:
            self.my_database_connection.close()
            logger.info("Disconnected from MySQL server.")