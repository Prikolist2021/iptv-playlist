#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Обёртка: скачивание -> фильтрация -> публикация в корень репозитория.
Запуск: python3 update_iptv.py  (локально или из GitHub Actions)"""
import os, sys, shutil
from datetime import datetime, timezone

REPO = os.path.dirname(os.path.abspath(__file__))
os.environ['IPTV_DIR'] = os.path.expanduser('~/iptv')   # рабочая папка вне git
sys.path.insert(0, REPO)
from iptv_tools import run_pipeline, p

README = """# IPTV playlist (auto-update)

Последнее обновление: {now} UTC
Каналов в плейлисте: {n}

## Ссылка для плееров (постоянная, содержимое обновляется само)

https://raw.githubusercontent.com/Prikolist2021/iptv-playlist/main/ru_sorted.m3u

## Что внутри

- Источник: IPTV_MEGA_PLAYLIST.m3u (~9000 каналов), скачивается автоматически.
- Фильтр: только русскоязычные каналы РФ / Беларуси / Украины.
- Убрано: зарубежные без русской дорожки, региональные и городские,
  врезки федеральных, таймшифты (+2/+4/+7), веб-камеры без звука, 18+,
  дубликаты (оставлено лучшее качество).
- Оставлено: федеральные, крупные новостные (Москва 24, Санкт-Петербург, 360),
  белорусские национальные, международные с русской дорожкой
  (TV BRICS, Deutsche Welle RU, Euronews RU, RT Док), тематические группы.

## Обновление

- Автоматически: GitHub Actions, каждый понедельник 03:00 UTC.
- Вручную: python3 update_iptv.py в папке репозитория.

Требования: Python 3.6+ (только стандартная библиотека).
"""

def main():
    now = datetime.now(timezone.utc)
    print('=== IPTV update:', now.strftime('%Y-%m-%d %H:%M UTC'), '===')
    os.makedirs(os.environ['IPTV_DIR'], exist_ok=True)
    if not run_pipeline(download=True):
        print('ОШИБКА: конвейер не завершился'); return 1
    src = p('ru_sorted.m3u')
    if not os.path.exists(src):
        print('ОШИБКА: нет ru_sorted.m3u'); return 1
    dst = os.path.join(REPO, 'ru_sorted.m3u')
    shutil.copy(src, dst)
    with open(dst, encoding='utf-8') as f:
        n = sum(1 for l in f if l.startswith('#EXTINF'))
    with open(os.path.join(REPO, 'README.md'), 'w', encoding='utf-8') as f:
        f.write(README.format(now=now.strftime('%Y-%m-%d %H:%M'), n=n))
    print('ГОТОВО: ru_sorted.m3u (%d каналов) + README.md' % n)
    return 0

if __name__ == '__main__':
    sys.exit(main())
