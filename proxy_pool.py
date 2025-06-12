import json
import os
import time
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

PROXY_STATS_PATH = "proxy_stats.json"
PROXY_BLACKLIST_PATH = "proxy_blacklist.json"
BLACKLIST_FAILS = 3

def save_proxy_state(proxy_pool):
    try:
        with open(PROXY_STATS_PATH, "w") as f:
            json.dump(proxy_pool.stats, f)
        with open(PROXY_BLACKLIST_PATH, "w") as f:
            json.dump(list(proxy_pool.bad_proxies), f)
    except Exception as e:
        logger.error(f"[ProxyPool] Failed to save state: {e}")

def load_proxy_state(proxy_pool):
    try:
        if os.path.exists(PROXY_STATS_PATH):
            with open(PROXY_STATS_PATH, "r") as f:
                stats = json.load(f)
                for k, v in stats.items():
                    proxy_pool.stats[k] = v
        if os.path.exists(PROXY_BLACKLIST_PATH):
            with open(PROXY_BLACKLIST_PATH, "r") as f:
                proxy_pool.bad_proxies = set(json.load(f))
    except Exception as e:
        logger.error(f"[ProxyPool] Failed to load state: {e}")

class ProxyPool:
    def __init__(self):
        self.stats = defaultdict(lambda: {'success': 0, 'fail': 0, 'last_fail': 0.0, 'consec_fail': 0})
        self.cooldown = 600
        self.bad_proxies = set()
        self.last_refresh = 0.0
        self.proxies = []
        load_proxy_state(self)

    async def refresh(self, fetch_func):
        now = time.time()
        if now - self.last_refresh < 600 and self.proxies:
            return
        self.proxies = await fetch_func()
        self.last_refresh = now
        logger.info(f"[ProxyPool] Refreshed proxies: {len(self.proxies)} available.")

    def get_proxy(self):
        now = time.time()
        candidates = [p for p in self.proxies if now - self.stats[p]['last_fail'] > self.cooldown and p not in self.bad_proxies]
        if not candidates:
            logger.warning("[ProxyPool] No proxies available outside cooldown/blacklist. Returning None.")
            return None
        candidates.sort(key=lambda p: (self.stats[p]['fail'], -self.stats[p]['success']))
        selected = candidates[0]
        logger.info(f"[ProxyPool] Selected proxy: {selected} (fail={self.stats[selected]['fail']}, success={self.stats[selected]['success']})")
        return selected

    def report(self, proxy, success, reason=None):
        if not proxy:
            return
        if success:
            self.stats[proxy]['success'] += 1
            self.stats[proxy]['consec_fail'] = 0
            logger.info(f"[ProxyPool] Proxy {proxy} succeeded.")
        else:
            self.stats[proxy]['fail'] += 1
            self.stats[proxy]['last_fail'] = float(time.time())
            self.stats[proxy]['consec_fail'] = self.stats[proxy].get('consec_fail', 0) + 1
            logger.warning(f"[ProxyPool] Proxy {proxy} failed. Reason: {reason}")
            if self.stats[proxy]['consec_fail'] >= BLACKLIST_FAILS:
                self.bad_proxies.add(proxy)
                logger.warning(f"[ProxyPool] Proxy {proxy} permanently blacklisted after {BLACKLIST_FAILS} consecutive fails.")
        save_proxy_state(self)

    def debug_state(self):
        logger.info(f"[ProxyPool] Current state:")
        for p in self.proxies:
            s = self.stats[p]
            logger.info(f"  {p}: success={s['success']}, fail={s['fail']}, last_fail={s['last_fail']}, consec_fail={s.get('consec_fail', 0)}")
        logger.info(f"[ProxyPool] Blacklisted: {self.bad_proxies}")
