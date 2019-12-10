import zipfile, os, datetime, logging
from smtplib import SMTP, SMTPRecipientsRefused, SMTPServerDisconnected
from email.message import EmailMessage

logger = logging.getLogger(__name__)

class Mail():
    smtp = None
    config_dict = {}

    def __init__(self, config_dict):
        self.config_dict = config_dict
        self.smtp = SMTP()

    def compress_log(self, log_file_name):
        logger.debug("Starting to compress {}...".format(os.path.basename(log_file_name)))
        compressed_log_file_name = "{}.zip".format(os.path.splitext(log_file_name)[0])
        with zipfile.ZipFile(compressed_log_file_name, 'w', compression=zipfile.ZIP_DEFLATED) as compressed_file:
            compressed_file.write(log_file_name)
        logger.info("Compressed {}.".format(os.path.basename(compressed_log_file_name)))
        return compressed_log_file_name

    def warn_about_results(self, scrapping_link, results_count, expected_results_count):
        logger.debug("Preparing e-mail message with warning about results count...")
        msg = EmailMessage()
        msg_plain_body = "Scrapping link\n" \
                         f"{scrapping_link}\n" \
                         f"should return at least {results_count} results\n" \
                         f"but returned {expected_results_count} results."
        msg.set_content(msg_plain_body)

        msg['Subject'] = f'Warning: Too few results'
        self.send_email(msg)

    def send_log(self, log_file_name=os.path.join(os.path.abspath(os.curdir), "scrapper-log.txt")):
        logger.debug("Preparing e-mail message with log...")
        log_file_name = self.compress_log(log_file_name)
        attachment_file_name = "{} scrapper-log.zip".format(datetime.date.today().isoformat())

        msg = EmailMessage()
        msg_plain_body = "Application encountered exception and it needs to be analyzed"
        msg.set_content(msg_plain_body)

        with open(log_file_name, 'rb') as log_file:
            log_content = log_file.read()
            msg.add_attachment(log_content, maintype="application", subtype="zip", filename=attachment_file_name)

        msg['Subject'] = f'Error: Encountered exception'
        self.send_email(msg)
        os.remove(log_file_name)

    def connect_to_smtp(self):
        logger.debug("Trying to connect to SMTP...")
        self.smtp.connect(host=self.config_dict["host"], port=self.config_dict["port"])
        logger.info("Connected to SMTP.")

    def log_in_to_smtp(self):
        logger.debug("Trying to log in to SMTP...")
        self.smtp.login(self.config_dict["username"], self.config_dict["password"])
        logger.info("Logged in to SMTP.")

    def send_email(self, msg):
        msg['From'] = self.config_dict["from_address"]
        msg['To'] = self.config_dict["to_address"]

        for send_email_try in range(3):
            try:
                self.smtp.send_message(msg)
                break
            except SMTPServerDisconnected:
                self.connect_to_smtp()
            except SMTPRecipientsRefused:
                self.log_in_to_smtp()

        logger.info("Sent e-mail to {}.".format(self.config_dict["to_address"]))

    def __del__(self):
        if self.smtp:
            self.smtp.close()