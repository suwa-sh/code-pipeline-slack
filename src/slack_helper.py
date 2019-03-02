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
# キャッシュせずに、つどslackのメッセージから対象を取得
# MSG_CACHE = {}


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
#    logger.debug("channels.history channel={}".format(ch))
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
#    cached = MSG_CACHE.get(buildInfo.executionId)
#    if cached:
#        return cached

    for m in find_my_messages(SLACK_CHANNEL):
        for att in msg_attachments(m):
            if att.get('footer') == buildInfo.executionId:
#                MSG_CACHE[buildInfo.executionId] = m
                return m
    return None


def msg_attachments(m):
    return m.get('attachments', [])


def msg_fields(m):
    for att in msg_attachments(m):
        for f in att['fields']:
            yield f


def post_build_msg(msgBuilder):
    #  logger.info("-- post_build_msg")
    #  logger.debug("---- MSG_CACHE: {}".format(json.dumps(MSG_CACHE, default=str)))
    #  logger.debug("---- CHANNEL_CACHE: {}".format(json.dumps(CHANNEL_CACHE, default=str)))

    if msgBuilder.messageId:
        ch_id = find_channel(SLACK_CHANNEL)
        msg = msgBuilder.message()
        r = update_msg(ch_id, msgBuilder.messageId, msg)
        #    logger.debug("---- response: {}".format(json.dumps(r, default=str)))
        if r['ok']:
            r['message']['ts'] = r['ts']
#            MSG_CACHE[msgBuilder.buildInfo.executionId] = r['message']
        return r

    r = send_msg(SLACK_CHANNEL, msgBuilder.message())
    if r['ok']:
         # logger.debug("---- response: {}".format(json.dumps(r, default=str)))
#        MSG_CACHE[msgBuilder.buildInfo.executionId] = r['message']
        CHANNEL_CACHE[SLACK_CHANNEL] = r['channel']

    return r


def send_msg(ch, attachments):
#    logger.info("---- send_msg")
#    logger.info("------ attachments: {}".format(attachments))
    r = sc_bot.api_call(
        "chat.postMessage",
        channel=ch,
        icon_emoji=SLACK_BOT_ICON,
        username=SLACK_BOT_NAME,
        attachments=attachments
        )
#    logger.info("------ res: {}".format(json.dumps(r)))
    return r


def update_msg(ch, ts, attachments):
#    logger.info("---- update_msg")
#    logger.info("------ attachments: {}".format(attachments))
    r = sc_bot.api_call(
        'chat.update',
        channel=ch,
        ts=ts,
        icon_emoji=SLACK_BOT_ICON,
        username=SLACK_BOT_NAME,
        attachments=attachments
#        attachments=[{
#            'color': 'good',
#            'fields': [{'short': True, 'value': 'TEST', 'title': 'twooca-CD-sandbox'}],
#            'footer': 'd8d56070-9a62-480c-90fa-07bc2975c2c1'
#        }]
        )
#    logger.info("------ res: {}".format(json.dumps(r)))
    return r
