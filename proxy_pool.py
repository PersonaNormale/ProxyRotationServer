import random
import requests
from logger_config import logger


def load_proxies(filepath):
    try:
        with open(filepath, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        logger.error(f"Proxy list file not found: {filepath}")
        return []
    except PermissionError:
        logger.error(f"PermissionDenied when trying to read {filepath}")
    except IOError as e:
        logger.error(
            f"IO error while trying to read proxy list from {filepath}: {e}")
        return []


def test_proxy(proxy):
    logger.info(f"Testing proxy: {proxy}")
    try:
        response = requests.get("https://www.google.com", proxies={
                                "http": f"http://{proxy}", "https": f"http://{proxy}"}, timeout=5)
        return response.status_code == 200
    except requests.ConnectTimeout:
        logger.error(f"Proxy {proxy} timed out")
        return False
    except requests.ConnectionError:
        logger.error(f"Connection error with proxy {proxy}")
        return False
    except requests.RequestException as e:
        logger.error(f"Proxy {proxy} failed: {e}")
        return False


# Proxy Pool


class ProxyPool:
    def __init__(self, proxy_file):
        self.proxies = self.load_and_verify_proxies(proxy_file)
        if not self.proxies:
            raise ValueError("No usable proxies found")

    @staticmethod
    def load_and_verify_proxies(proxy_file):
        proxies = load_proxies(proxy_file)
        return [proxy for proxy in proxies if test_proxy(proxy)]

    def get_proxy(self):
        return random.choice(self.proxies)
