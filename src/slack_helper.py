# -*- coding: utf-8 -*-

from slackclient import SlackClient
import os
import json
import logging
logger = logging.getLogger()
#logger.setLevel(logging.INFO)

sc = SlackClient(os.getenv("SLACK_TOKEN"))
sc_bot = SlackClient(os.getenv("SLACK_BOT_TOKEN"))
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL", "builds2")
SLACK_BOT_NAME = os.getenv("SLACK_BOT_NAME", "BuildBot")
SLACK_BOT_ICON = os.getenv("SLACK_BOT_ICON", ":robot_face:")

CHANNEL_CACHE = {}


def find_channel(name):
    if name in CHANNEL_CACHE:
        return CHANNEL_CACHE[name]

    r = sc.api_call("channels.list", exclude_archived=1)
    if 'error' in r:
        logger.error("{} channels.list error: {}".format(__name__, r['error']))
        return None

    for ch in r['channels']:
        if ch['name'] == name:
            CHANNEL_CACHE[name] = ch['id']
            return ch['id']

    return None


def find_msg(ch):
    r = sc.api_call('channels.history', channel=ch)
    if 'error' in r:
        logger.error("{} channels.history error: {}".format(__name__, r['error']))
        return None

    return r


def find_my_messages(ch_name, user_name=SLACK_BOT_NAME):
    ch_id = find_channel(ch_name)
    msg = find_msg(ch_id)
    for m in msg['messages']:
        if m.get('username') == user_name:
            yield m


def find_message_for_build(buildInfo):
    for m in find_my_messages(SLACK_CHANNEL):
        for att in msg_attachments(m):
            if att.get('footer') == buildInfo.executionId:
                return m
    return None


def msg_attachments(m):
    return m.get('attachments', [])


def msg_fields(m):
    for att in msg_attachments(m):
        for f in att['fields']:
            yield f


def post_build_msg(msgBuilder):
    if msgBuilder.isClear:
        ch_id = find_channel(SLACK_CHANNEL)
        res = clear_msg(ch_id, msgBuilder.messageId)
        if res['ok']:
            res['message']['ts'] = res['ts']
        return res

    if msgBuilder.messageId:
        ch_id = find_channel(SLACK_CHANNEL)
        msg = msgBuilder.message()
        res = update_msg(ch_id, msgBuilder.messageId, msg)
        if res['ok']:
            res['message']['ts'] = res['ts']
        return res

    res = send_msg(SLACK_CHANNEL, msgBuilder.message())
    if res['ok']:
        CHANNEL_CACHE[SLACK_CHANNEL] = res['channel']

    return res


def send_msg(ch, attachments):
    res = sc_bot.api_call(
        "chat.postMessage",
        channel=ch,
        icon_emoji=SLACK_BOT_ICON,
        username=SLACK_BOT_NAME,
        attachments=attachments
    )
    return res


def update_msg(ch, ts, attachments):
    res = sc_bot.api_call(
        'chat.update',
        channel=ch,
        ts=ts,
        icon_emoji=SLACK_BOT_ICON,
        username=SLACK_BOT_NAME,
        attachments=attachments
    )
    return res


def clear_msg(ch, ts):
    res = sc_bot.api_call(
        'chat.update',
        channel=ch,
        ts=ts,
        icon_emoji=SLACK_BOT_ICON,
        username=SLACK_BOT_NAME,
        attachments=[{
            'color': 'good',
            'fields': [{'short': True, 'value': 'TEST', 'title': 'twooca-CD-sandbox'}],
            'footer': 'd8d56070-9a62-480c-90fa-07bc2975c2c1'
        }]
    )
    return res
