import logging
import os
import random
from typing import List, Optional

import requests

logger = logging.getLogger(__name__)


class ProxyManager:
    def __init__(self):
        self.proxies = []
        self.current_index = 0
        self.load_proxies()

    def load_proxies(self):
        """Load proxies from environment variable or fetch free proxies"""
        webshare_proxies = os.getenv("WEBSHARE_PROXIES", "")

        if webshare_proxies:
            self._load_webshare_proxies(webshare_proxies)
        else:
            self.fetch_proxies()

    def _load_webshare_proxies(self, proxy_string: str):
        """
        Load Webshare proxies from environment variable
        """
        try:
            proxy_list = proxy_string.split(",")

            for proxy_data in proxy_list:
                parts = proxy_data.strip().split(":")
                if len(parts) == 4:
                    host, port, username, password = parts
                    proxy_url = f"http://{username}:{password}@{host}:{port}"

                    self.proxies.append({"http": proxy_url, "https": proxy_url})

            logger.info(f"[ProxyManager] Loaded {len(self.proxies)} Webshare proxies")
        except Exception as e:
            logger.error(f"[ProxyManager] Error loading Webshare proxies: {str(e)}")
            self.fetch_proxies()

    def fetch_proxies(self):
        """Fetch free proxies from multiple sources"""
        try:
            sources = [
                self._fetch_from_proxyscrape,
                self._fetch_from_geonode,
                self._fetch_from_proxy_list,
            ]

            for source_func in sources:
                try:
                    proxies = source_func()
                    if proxies:
                        self.proxies.extend(proxies)
                        logger.info(
                            f"[ProxyManager] Fetched proxies from {source_func.__name__}"
                        )
                except Exception as e:
                    logger.warning(
                        f"[ProxyManager] Failed to fetch from {source_func.__name__}: {str(e)}"
                    )

            unique_proxies = []
            seen = set()
            for proxy in self.proxies:
                proxy_str = proxy.get("http", "")
                if proxy_str not in seen:
                    seen.add(proxy_str)
                    unique_proxies.append(proxy)

            self.proxies = unique_proxies
            logger.info(f"[ProxyManager] Total unique proxies: {len(self.proxies)}")

        except Exception as e:
            logger.error(f"[ProxyManager] Error fetching proxies: {str(e)}")

    def _fetch_from_proxyscrape(self) -> List[dict]:
        """Fetch from ProxyScrape API"""
        url = "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            proxy_list = response.text.strip().split("\n")
            return [
                {"http": f"http://{proxy.strip()}", "https": f"http://{proxy.strip()}"}
                for proxy in proxy_list[:20]
                if proxy.strip()
            ]
        return []

    def _fetch_from_geonode(self) -> List[dict]:
        """Fetch from GeoNode free proxy API"""
        url = "https://proxylist.geonode.com/api/proxy-list?limit=20&page=1&sort_by=lastChecked&sort_type=desc&protocols=http%2Chttps"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            proxies = []

            for proxy_data in data.get("data", [])[:10]:
                ip = proxy_data.get("ip")
                port = proxy_data.get("port")

                if ip and port:
                    proxies.append(
                        {"http": f"http://{ip}:{port}", "https": f"http://{ip}:{port}"}
                    )

            return proxies
        return []

    def _fetch_from_proxy_list(self) -> List[dict]:
        """Fetch from Proxy-List.download API"""
        url = "https://www.proxy-list.download/api/v1/get?type=http"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            proxy_list = response.text.strip().split("\r\n")
            return [
                {"http": f"http://{proxy.strip()}", "https": f"http://{proxy.strip()}"}
                for proxy in proxy_list[:20]
                if proxy.strip()
            ]
        return []

    def get_proxy(self) -> Optional[dict]:
        """Get next proxy in rotation"""
        if not self.proxies:
            return None

        proxy = self.proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.proxies)
        return proxy

    def get_random_proxy(self) -> Optional[dict]:
        """Get random proxy"""
        if not self.proxies:
            return None
        return random.choice(self.proxies)

    def test_proxy(self, proxy: dict) -> bool:
        """Test if proxy works"""
        try:
            response = requests.get("https://httpbin.org/ip", proxies=proxy, timeout=5)
            return response.status_code == 200
        except:
            return False

    def get_working_proxy(self) -> Optional[dict]:
        """Get a working proxy (tests up to 10 proxies)"""
        if not self.proxies:
            logger.warning("[ProxyManager] No proxies available")
            return None

        if os.getenv("WEBSHARE_PROXIES"):
            return self.get_random_proxy()

        tested = 0
        max_tests = min(10, len(self.proxies))

        for _ in range(max_tests):
            proxy = self.get_random_proxy()
            tested += 1

            if self.test_proxy(proxy):
                logger.info(f"[ProxyManager] Found working proxy (tested {tested})")
                return proxy

        logger.warning(
            f"[ProxyManager] No working proxies found after testing {tested}"
        )
        return None

    def remove_proxy(self, proxy: dict):
        """Remove a bad proxy from the list"""
        try:
            self.proxies.remove(proxy)
            logger.info(
                f"[ProxyManager] Removed bad proxy. Remaining: {len(self.proxies)}"
            )
        except ValueError:
            pass


proxy_manager = ProxyManager()
