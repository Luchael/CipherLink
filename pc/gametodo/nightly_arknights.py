"""Opt-in ArkPRTS Korean-server 23:59 KST once-per-day account observation.

Requires PC process running at 23:59; may kick player out even once; local user consents.
Never sends credentials to third-party proxy, uses locally stored ArkPRTS Yostar credentials.
"""
from datetime import datetime, timezone, timedelta
from pathlib import Path
import logging
import time

from .lookup_policy import enabled
from .account_watch import run_account_check

KST = timezone(timedelta(hours=9))
LOG = logging.getLogger(__name__)


def eligible(settings, moment):
    local = moment.astimezone(KST)
    a = settings.get('account_data') or {}
    return (enabled(settings, 'arknights') and a.get('enabled') is True
            and (a.get('arknights') or {}).get('enabled') is True
            and local.hour == 23 and local.minute == 59)


def once(settings, api=None, store=None, moment=None, directory=None):
    """At most one login attempt per KST date, including if the request fails.

    Returns False if disabled/not in the 23:59 minute/already attempted.
    """
    moment = moment or datetime.now(KST)
    if not eligible(settings, moment):return False
    folder = Path(directory) if directory is not None else Path.home()/'.gametodo'/'arknights_daily_attempts'
    folder.mkdir(parents=True,exist_ok=True)
    date = moment.astimezone(KST).strftime('%Y-%m-%d')
    claim = folder/f'{date}.attempt'
    try:
        with claim.open('x',encoding='utf-8') as f:f.write('attempted\n')
    except FileExistsError:
        return False
    # No retries that day even after an auth failure: guarantee one session-impactful attempt.
    try:
        rows = run_account_check(settings, api, store, now=moment,
                                 only_game='arknights', allow_arknights=True,
                                 read_only=(api is None or store is None))
        for result in rows:
            LOG.info('ArkPRTS daily: %s', result.get('action',''))
    except Exception as exc:
        LOG.warning('ArkPRTS daily query failed: %s', type(exc).__name__)
    return True


def wait_loop(settings, api=None, store=None, stop=None):
    """Only the main PC 'run' process owns this loop; no OS cron/task installs."""
    while stop is None or not stop.is_set():
        once(settings, api, store)
        if stop is None:time.sleep(10)
        else:stop.wait(10)
