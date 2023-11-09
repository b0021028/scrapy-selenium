"""This module contains the ``SeleniumRequest`` class"""

from scrapy import Request


class SeleniumRequest(Request):
    """Scrapy ``Request`` subclass providing additional arguments"""

    def __init__(self, wait_time=None, wait_until=None, screenshot=False, script_dict_list=None, timeout=None, *args, **kwargs):
        """Initialize a new selenium request

        Parameters
        ----------
        wait_time: int
            The number of seconds to wait.
        wait_until: method
            One of the "selenium.webdriver.support.expected_conditions". The response
            will be returned until the given condition is fulfilled.
        screenshot: bool
            If True, a screenshot of the page will be taken and the data of the screenshot
            will be returned in the response "meta" attribute.
        script: list of dictionaries. Each
            dictionary represents a script to be executed by the Selenium driver. Each
            dictionary in the list can have the following keys: script, wait, pause
        timeout: float
            timeout specifies the number of seconds before a TimeoutError occurs if the page loads slowly.
        """

        self.wait_time = wait_time
        self.wait_until = wait_until
        self.screenshot = screenshot
        self.script_dict_list = script_dict_list

        self.timeout = timeout

        super().__init__(*args, **kwargs)
