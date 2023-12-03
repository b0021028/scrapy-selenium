"""This module contains the ``SeleniumMiddleware`` scrapy middleware"""

from importlib import import_module

from scrapy import signals
from scrapy.exceptions import NotConfigured
from selenium.webdriver.support.ui import WebDriverWait

# timeout
from selenium.common.exceptions import TimeoutException
from twisted.internet.error import TimeoutError
from scrapy.exceptions import IgnoreRequest


from .http import SeleniumRequest
from .selenium_utilities import SeleniumUtilities


class SeleniumMiddleware:
    """Scrapy middleware handling the requests using selenium"""

    def __init__(self, driver_name, driver_executable_path,
        browser_executable_path, command_executor, driver_arguments,
        timeout):
        """Initialize the selenium webdriver

        Parameters
        ----------
        driver_name: str
            The selenium ``WebDriver`` to use
        driver_executable_path: str
            The path of the executable binary of the driver
        driver_arguments: list
            A list of arguments to initialize the driver
        browser_executable_path: str
            The path of the executable binary of the browser
        command_executor: str
            Selenium remote server endpoint
        timeout: int
            support DOWNLOAD_TIMEOUT
        """

        self.timeout = timeout

        webdriver_base_path = f'selenium.webdriver.{driver_name}'

        driver_klass_module = import_module(f'{webdriver_base_path}.webdriver')
        driver_klass = getattr(driver_klass_module, 'WebDriver')

        driver_options_module = import_module(f'{webdriver_base_path}.options')
        driver_options_klass = getattr(driver_options_module, 'Options')

        driver_options = driver_options_klass()

        if(browser_executable_path):
            driver_options.binary_location = browser_executable_path
        for argument in driver_arguments:
            driver_options.add_argument(argument)

        # locally installed driver
        if(driver_executable_path is not None):
            service_module = import_module(f'{webdriver_base_path}.service')
            service_klass = getattr(service_module, 'Service')
            service_kwargs = {
                'executable_path': driver_executable_path,
            }
            service = service_klass(**service_kwargs)
            driver_kwargs = {
                'service': service,
                'options': driver_options
            }
            self.driver = driver_klass(**driver_kwargs)
        # remote driver
        elif(command_executor is not None):
            from selenium import webdriver
            self.driver = webdriver.Remote(command_executor=command_executor,
                                           options=driver_options)

    @classmethod
    def from_crawler(cls, crawler):
        """Initialize the middleware with the crawler settings"""

        driver_name = crawler.settings.get('SELENIUM_DRIVER_NAME')
        driver_executable_path = crawler.settings.get('SELENIUM_DRIVER_EXECUTABLE_PATH')
        browser_executable_path = crawler.settings.get('SELENIUM_BROWSER_EXECUTABLE_PATH')
        command_executor = crawler.settings.get('SELENIUM_COMMAND_EXECUTOR')
        driver_arguments = crawler.settings.get('SELENIUM_DRIVER_ARGUMENTS')

        timeout = crawler.settings.getfloat('DOWNLOAD_TIMEOUT')

        if(driver_name is None):
            raise NotConfigured('SELENIUM_DRIVER_NAME must be set')

        if(driver_executable_path is None and command_executor is None):
            raise NotConfigured('Either SELENIUM_DRIVER_EXECUTABLE_PATH '
                                'or SELENIUM_COMMAND_EXECUTOR must be set')

        middleware = cls(
            driver_name=driver_name,
            driver_executable_path=driver_executable_path,
            browser_executable_path=browser_executable_path,
            command_executor=command_executor,
            driver_arguments=driver_arguments,
            timeout=timeout,
        )

        crawler.signals.connect(middleware.spider_closed, signals.spider_closed)

        return middleware

    def process_request(self, request, spider):
        """Process a request using the selenium driver if(applicable"""

        if(not isinstance(request, SeleniumRequest)):
            return None


        # timeout
        timeout = request.timeout
        if timeout is None:
            timeout = self.timeout
        if not isinstance(timeout, (int, float)):
            # default 30s
            timeout = 30
        self.driver.set_page_load_timeout(timeout)



        try:
            self.driver.get(request.url)
        except TimeoutException as e:
            raise IgnoreRequest(TimeoutError(e, "scrapy-selenium : request timeout"))

        if request.cookies:
            if hasattr(request.cookies, "__iter__"):
                for cookie in request.cookies:
                    self.driver.add_cookie(cookie)
            else:
                for cookie_name, cookie_value in request.cookies.items():
                    self.driver.add_cookie(
                        {
                            'name': cookie_name,
                            'value': cookie_value
                        }
                    )

            try:
                self.driver.get(request.url)
            except TimeoutException as e:
                raise IgnoreRequest(TimeoutError(e, "scrapy-selenium : request timeout"))



        if(request.wait_until):
            WebDriverWait(self.driver, request.wait_time).until(
                request.wait_until
            )

        if(request.screenshot):
            request.meta['screenshot'] = self.driver.get_screenshot_as_png()

        if(request.script_dict_list and len(request.script_dict_list)):
            SeleniumUtilities.handle_selenium_scripts(driver=self.driver, script_dict_list=request.script_dict_list)

        return SeleniumUtilities.generate_scrapy_response(driver=self.driver, request=request)

    def spider_closed(self):
        """Shutdown the driver when spider is closed"""
        self.driver.quit()
