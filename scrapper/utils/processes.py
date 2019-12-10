import psutil, os



def ensure_web_browser_is_not_running():
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        if proc.info["name"] == "firefox" and \
        "-marionette" in proc.info["cmdline"]:
            print("Found running Firefox. Killing it.")
            proc.kill()

def is_another_scrapper_instance_present():
    for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
        if proc.info["name"] == "python3" and \
        "scrapper" in proc.info["cmdline"] and \
        os.getpid() != proc.info["pid"]:
            print("Scrapper already running. Not starting another instnce.")
            return True
    return False