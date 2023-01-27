import re
import io
import os
import sys
import json
import time
import logging
import hashlib
import platform
import calendar
import datetime
import threading
from pathlib import Path
from itertools import islice
from functools import lru_cache, wraps
from dataclasses import dataclass, asdict
from typing import Optional, List

class 假的io(io.StringIO):    # pythonw.exe 启动时，sys.stdout 会被重定向到 None，导致一些库无法正常工作，所以骗一骗它们
    write = flush = lambda *a, **k: None
if sys.stdout is None:
    sys.stdout = 假的io()
if sys.stderr is None:
    sys.stderr = 假的io()

import fire
import yaml
import requests
import feedparser
import flask
import flask_gzip
from rimo_storage import 超dict


support_toast = platform.system() == 'Windows' and platform.version()[:2] in ('10', '11')
if support_toast:
    from win10toast_click import ToastNotifier

logging.getLogger('werkzeug').setLevel(logging.ERROR)
此处 = Path(__file__).absolute().parent


@dataclass(repr=False)
class 源:
    url: str
    name: Optional[str] = None
    filter: Optional[str] = None
    interval: int = 10 * 60


def entry_time(e) -> float:
    if t := e.get('published_parsed'):
        return calendar.timegm(t)
    if t := e.get('updated_parsed'):
        return calendar.timegm(t)
    return e['_first_fetch_time']


class 抓捕io:
    def __init__(self, io=sys.stdout, max_size=1024 * 1024):
        self.terminal = io
        self.log = ''
        self._max_size = max_size

    def write(self, message):
        self.terminal.write(message)
        self.log += message
        if len(self.log) > self._max_size:
            self.log = self.log[-int(self._max_size * 0.8):]

    def flush(self):
        self.terminal.flush()


sys.stdout = 抓捕io(sys.stdout)
sys.stderr = 抓捕io(sys.stderr)


全局存储 = 超dict(Path.home()/'.rimo-rss-reader/savedata/global_storage', compress='zlib', serialize='json')
meta = {}

@lru_cache(maxsize=999)
def 存储(url):
    sha = hashlib.sha224(url.encode('utf8')).hexdigest()
    return 超dict(Path.home()/'.rimo-rss-reader/savedata/feed'/sha, compress='zlib', serialize='json')


def _相等(a, b):
    a = json.loads(json.dumps(a))
    b = json.loads(json.dumps(b))
    del a['_fetch_time']
    del b['_fetch_time']
    return a == b


def get_feed(url):
    d = 存储(url)
    索引 = d.get('_索引', {})
    feed = feedparser.parse(requests.get(url, timeout=15).content, sanitize_html=False, resolve_relative_uris=False)
    entries = feed.pop('entries')
    全局存储['meta'] = {**全局存储.get('meta', {}), url: feed}
    meta[url] = feed
    t = time.time()
    for i, e in enumerate(entries):
        e['_first_fetch_time'] = e['_fetch_time'] = t - 0.00001 * i
        e['_read'] = False
    小d = {}
    不重复条目 = [i for i in entries if i['id'] not in 索引]
    for e in entries:
        h = str(int(entry_time(e)) // 3600)
        if e['id'] in 索引:
            h = 索引[e['id']]
        else:
            索引[e['id']] = h
        小d.setdefault(h, {})[e['id']] = e
    d['_索引'] = 索引
    相等个数 = 0
    for k, v in 小d.items():
        大v = d.get(k, {})
        for kk, vv in v.items():
            if kk in 大v:
                vv['_first_fetch_time'] = 大v[kk]['_first_fetch_time']
                vv['_read'] = 大v[kk]['_read']
                相等个数 += _相等(vv, 大v[kk])
            大v[kk] = vv
        d[k] = 大v
    print(f'{url} 更新完成。获取 {len(entries)} 个条目，其中id重复 {len(entries)-len(不重复条目)} 个，{相等个数} 个条目内容也相同。')
    return 不重复条目


最后访问时间 = {}
def 循环():
    while True:
        更新的订阅组 = []
        for name, v in 配置['订阅组'].items():
            for i in v:
                k = i.url, i.interval
                if 最后访问时间.get(k, 0) + i.interval < time.time():
                    print(f'[{datetime.datetime.now()}]【{name}】访问 {i.url}')
                    try:
                        es = get_feed(i.url)
                    except Exception as e:
                        logging.exception(e)
                    else:
                        最后访问时间[k] = time.time()
                        es = [e for e in es if (not i.filter or re.fullmatch(i.filter, e['title']))]
                        if es:
                            更新的订阅组.append(name)
        if 更新的订阅组:
            print(f'订阅组{"、".join(更新的订阅组)}更新了')
            if support_toast and 配置['windows通知']:
                ToastNotifier().show_toast(
                    'rimo-rss-reader',
                    f'订阅组{"、".join(更新的订阅组)}更新了，点开看看 >>',
                    icon_path=此处 / 'web\i.ico',
                    threaded=True,
                    callback_on_click=lambda: os.system('start http://127.0.0.1:23333/')
                )
        time.sleep(60)


def _it(ss: List[源], 开始时间: float = 1e+100):
    a = {}
    for s in ss:
        for k in 存储(s.url).keys():
            if k.startswith('_'):
                continue
            if int(k) > int(开始时间) // 3600 + 1:
                continue
            a.setdefault(int(k), []).append(s)
    for k, v in sorted(a.items())[::-1]:
        es = []
        for s in v:
            for e in 存储(s.url)[str(k)].values():
                e['_feed_url'] = s.url
                e['_entry_time'] = entry_time(e)
                if not s.filter or re.fullmatch(s.filter, e['title']):
                    if entry_time(e) < 开始时间:
                        es.append(e)
        yield from sorted(es, key=entry_time)[::-1]


def it(ss: List[源], 开始时间: float = 1e+100, 最多数量: int = 100):
    return islice(_it(ss, 开始时间), 最多数量)


def 好(rule: str, return_json=True):
    def ff(f):
        @wraps(f)
        def fff():
            d = dict(flask.request.args)
            if flask.request.data:
                d.update(json.loads(flask.request.data))
            print(f'[{datetime.datetime.now()}] 调用: {f.__name__}, {d}')
            res = f(**d)
            if return_json:
                return app.response_class(
                    response=json.dumps(res, indent=2, default=asdict),
                    status=200,
                    mimetype='application/json',
                )
            else:
                return app.response_class(
                    response=res,
                    status=200,
                    mimetype='text/plain',
                )
        return app.route(rule, methods=['GET', 'POST'])(fff)
    return ff


app = flask.Flask(__name__)
flask_gzip.Gzip(app)


@好('/超喂')
def 超喂(源: list[str], 开始时间: float = 1e+100, 最多数量: int = 100):
    return {i: [*it(配置['订阅组'][i], 开始时间, 最多数量)] for i in 源}


@好('/所有订阅组')
def 所有订阅组():
    meta存储 = 全局存储.get('meta', {})
    for k, v in 配置['订阅组'].items():
        for i in v:
            if i.name is None and (m := (meta.get(i.url, {}) or meta存储.get(i.url, {}))):
                i.name = m.get('feed', {}).get('title')
    return 配置['订阅组']


@好('/标为已读')
def 标为已读(feed_url, entry_time, id):
    h = str(int(float(entry_time)) // 3600)
    t = 存储(feed_url)[h]
    t[id]['_read'] = True
    存储(feed_url)[h] = t


@好('/全部标为已读')
def 全部标为已读(feed_url):
    for k, v in [*存储(feed_url).items()]:
        if k.startswith('_'):
            continue
        存储(feed_url)[k] = {kk: {**vv, '_read': True} for kk, vv in v.items()}


@好('/log', return_json=False)
def get_log(name):
    if name == 'stdout':
        return sys.stdout.log
    elif name == 'stderr':
        return sys.stderr.log


@app.route('/<path:path>')
def s(path):
    return flask.send_from_directory('web', path)


@app.route('/')
def _():
    return flask.send_from_directory('web', 'u.html')


def main(config: str):
    global 配置
    配置 = yaml.safe_load(open(config, 'r', encoding='utf8'))
    for k, v in 配置['订阅组'].items():
        配置['订阅组'][k] = [源(**t) if isinstance(t, dict) else 源(t) for t in v]
    threading.Thread(target=循环, daemon=True).start()
    host = '127.0.0.1'
    if 配置['别的电脑也可以看']:
        host = '0.0.0.0'
    app.run(host, 配置['端口号'], threaded=False)


if __name__ == '__main__':
    fire.Fire(main)
