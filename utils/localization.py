"""Language-neutral catalog access. Safe to import without Blender or on workers."""
import json
from pathlib import Path
import re

ENGLISH = json.loads((Path(__file__).resolve().parents[1] / 'locales' / 'fab.en.json').read_text(encoding='utf-8'))


def normalize_language(language, system_language='en_US'):
    code = str(language or '').replace('-', '_')
    if not code or code.upper() in ('DEFAULT', 'AUTO'):
        code = str(system_language or 'en_US').replace('-', '_')
    return 'zh_CN' if code.split('_')[0].lower() == 'zh' else 'en_US'


def translate(key, language):
    return key if normalize_language(language) == 'zh_CN' else ENGLISH.get(key, key)


def translate_message(message, language):
    """Translate our saved status templates; preserve filenames and native error details.

    Call only for status/error/detail fields, never for product names or paths.
    Worker results stay language-neutral so changing the UI language needs no rescan.
    """
    if normalize_language(language) == 'zh_CN' or not message:
        return message
    if message in ENGLISH:
        return ENGLISH[message]
    for source, target in ENGLISH.items():
        if '%s' in source or '%d' in source:
            parts = re.split(r'(%[sd])', source)
            pattern = ''.join('(.*?)' if p == '%s' else r'(\d+)' if p == '%d' else re.escape(p) for p in parts)
            match = re.fullmatch(pattern, message, flags=re.DOTALL)
            if match:
                values = iter(match.groups())
                args = tuple(int(next(values)) if p == '%d' else next(values) for p in parts if p in ('%s', '%d'))
                return target % args
    for source in sorted(ENGLISH, key=len, reverse=True):
        if source.endswith(('：', ': ', ' · ', '： ', '\n')) and message.startswith(source):
            return ENGLISH[source] + translate_message(message[len(source):], language)
    first, separator, rest = message.partition(' · ')
    if separator and first in ENGLISH:
        return ENGLISH[first] + separator + rest
    suffix = '（导入记录未保存）'
    if message.endswith(suffix):
        return translate_message(message[:-len(suffix)], language) + ENGLISH[suffix]
    return message
