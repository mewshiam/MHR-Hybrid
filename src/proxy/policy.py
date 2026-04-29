import time

from constants import (
    GOOGLE_DIRECT_ALLOW_EXACT,
    GOOGLE_DIRECT_ALLOW_SUFFIXES,
    GOOGLE_DIRECT_EXACT_EXCLUDE,
    GOOGLE_DIRECT_SUFFIX_EXCLUDE,
    GOOGLE_OWNED_EXACT,
    GOOGLE_OWNED_SUFFIXES,
    LARGE_FILE_EXTS,
    SNI_REWRITE_SUFFIXES,
    TRACE_HOST_SUFFIXES,
)


class ProxyPolicy:
    _GOOGLE_DIRECT_EXACT_EXCLUDE = GOOGLE_DIRECT_EXACT_EXCLUDE
    _GOOGLE_DIRECT_SUFFIX_EXCLUDE = GOOGLE_DIRECT_SUFFIX_EXCLUDE
    _GOOGLE_DIRECT_ALLOW_EXACT = GOOGLE_DIRECT_ALLOW_EXACT
    _GOOGLE_DIRECT_ALLOW_SUFFIXES = GOOGLE_DIRECT_ALLOW_SUFFIXES
    _TRACE_HOST_SUFFIXES = TRACE_HOST_SUFFIXES
    _GOOGLE_OWNED_SUFFIXES = GOOGLE_OWNED_SUFFIXES
    _GOOGLE_OWNED_EXACT = GOOGLE_OWNED_EXACT
    _DOWNLOAD_DEFAULT_EXTS = tuple(sorted(LARGE_FILE_EXTS))
    _SNI_REWRITE_SUFFIXES = SNI_REWRITE_SUFFIXES
    _YOUTUBE_SNI_SUFFIXES = frozenset({"youtube.com", "youtu.be", "youtube-nocookie.com"})

    @staticmethod
    def _load_host_rules(raw):
        exact, suffixes = set(), []
        for item in raw or []:
            h = str(item).strip().lower().rstrip('.')
            if not h:
                continue
            if h.startswith('.'):
                suffixes.append(h)
            else:
                exact.add(h)
        return exact, tuple(suffixes)

    @staticmethod
    def _host_matches_rules(host, rules):
        exact, suffixes = rules
        h = host.lower().rstrip('.')
        return h in exact or any(h.endswith(s) for s in suffixes)

    def _is_blocked(self, host): return self._host_matches_rules(host, self._block_hosts)
    def _is_bypassed(self, host): return self._host_matches_rules(host, self._bypass_hosts)
    def _direct_temporarily_disabled(self, host):
        h = host.lower().rstrip('.')
        now = time.time(); disabled = False
        for key in self._direct_failure_keys(h):
            until = self._direct_fail_until.get(key, 0)
            if until > now: disabled = True
            else: self._direct_fail_until.pop(key, None)
        return disabled
    def _remember_direct_failure(self, host, ttl=600):
        until = time.time() + ttl
        for key in self._direct_failure_keys(host.lower().rstrip('.')):
            self._direct_fail_until[key] = until
