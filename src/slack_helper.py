# -*- coding: utf-8 -*-

from slackclient import SlackClient
from time import sleep
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
SLACK_FIND_MESSAGE_TIMEOUT_SEC = int(os.getenv("SLACK_FIND_MESSAGE_TIMEOUT_SEC", 5))
SLACK_FIND_MESSAGE_WAIT_SEC = int(os.getenv("SLACK_FIND_MESSAGE_WAIT_SEC", 1))
CHANNEL_CACHE = {}

channel_id = os.getenv("SLACK_CHANNEL_ID", None)
if channel_id:
    CHANNEL_CACHE[SLACK_CHANNEL] = channel_id


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
        logger.warning("{} channels.history error: {}".format(__name__, r['error']))
        return find_private_msg(ch)
    return r


def find_private_msg(ch):
    r = sc.api_call('groups.history', channel=ch)
    if 'error' in r:
        logger.error("{} groups.history error: {}".format(__name__, r['error']))
        return None
    return r


def find_my_messages(ch_name, user_name=SLACK_BOT_NAME):
    ch_id = find_channel(ch_name)
    msg = find_msg(ch_id)
    for m in msg['messages']:
        if m.get('username') == user_name:
            yield m

def find_message_for_build_by_execution_id(execution_id):
    logger.info('---- find_message_for_build_by_execution_id execution_id:{}'.format(execution_id))
    for m in find_my_messages(SLACK_CHANNEL):
        for att in msg_attachments(m):
            if att.get('footer') == execution_id:
                return m
    return None

def find_message_for_build(build_info):
    logger.info('-- find_message_for_build build_info:{}'.format(vars(build_info)))
    if build_info.isStarted:
        return None

    # started以外は、すでに同一executionIdのメッセージが存在するはず
    for i in range(SLACK_FIND_MESSAGE_TIMEOUT_SEC):
        message = find_message_for_build_by_execution_id(build_info.executionId)
        logger.info('---- message:{}'.format(json.dumps(message)))
        if message:
            return message
        logger.info('---- wait count: {}'.format(i))
        sleep(SLACK_FIND_MESSAGE_WAIT_SEC)

    return None


def msg_attachments(m):
    return m.get('attachments', [])


def msg_fields(m):
    for att in msg_attachments(m):
        for f in att['fields']:
            yield f


def post_build_msg(msgBuilder):
    if msgBuilder.isStarted:
        res = send_msg(SLACK_CHANNEL, msgBuilder.message())
        if res['ok']:
            CHANNEL_CACHE[SLACK_CHANNEL] = res['channel']

        return res

    if msgBuilder.messageId is None:
        logger.error('msgBuilder: {}'.format(vars(msgBuilder)))
        raise ValueError("msgBuilder.messageId is required.")

    ch_id = find_channel(SLACK_CHANNEL)
    msg = msgBuilder.message()
    res = update_msg(ch_id, msgBuilder.messageId, msg)
    if res['ok']:
        res['message']['ts'] = res['ts']
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
