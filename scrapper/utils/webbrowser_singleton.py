from scrapper.utils.webbrowser import WebBrowser

def get_web_browser_instance(headless=True):
    global web_browser_singleton
    try:
        return web_browser_singleton
    except NameError:
        web_browser_singleton = WebBrowser(headless)
        return web_browser_singleton