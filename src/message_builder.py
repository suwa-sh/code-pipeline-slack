# -*- coding: utf-8 -*-

from collections import OrderedDict

import json
import logging
logger = logging.getLogger()
#logger.setLevel(logging.INFO)


class MessageBuilder(object):
    def __init__(self, build_info, message):
        self.buildInfo = build_info
        self.actions = []
        self.messageId = None
        self.isStarted = False

        logger.info("MessageBuilder#__init__ build_info:{}, message:{}".format(vars(build_info), json.dumps(message)))
        if message:
            att = message['attachments'][0]
            self.fields = att['fields']
            self.actions = att.get('actions', [])
            self.messageId = message['ts']
            return

        # logger.info("Actions {}".format(self.actions))
        self.fields = [
            {
                "title" : build_info.pipeline,
                "value" : "UNKNOWN",
                "short" : True
            },
            {
                "title": "Stages",
                "value": "",
                "short": True
            }
        ]

    def hasField(self, name):
        return len([f for f in self.fields if f['title'] == name]) > 0

    def needsRevisionInfo(self):
        return not self.hasField('Revision')

    def attachRevisionInfo(self, rev):
        if not self.needsRevisionInfo():
            return
        if rev is None:
            return

        if 'revisionUrl' in rev:
            url = rev['revisionUrl']
            commit = rev['revisionId'][:7]
            message = rev['revisionSummary'].encode('utf-8')
            self.fields.append({
                "title": "Revision",
                "value": "<{}|{}: {}>".format(url, commit, message),
                "short": False
            })
            return

        self.fields.append({
            "title": "Revision",
            "value": rev['revisionSummary'],
            "short": False
        })

    def attachLogs(self, logs):
        self.findOrCreateAction('Build Logs', logs['deep-link'])

    def findOrCreateAction(self, name, link):
        for action in self.actions:
            if action['text'] == name:
                return action

        action = { "type": "button", "text": name, "url": link }
        self.actions.append(action)
        return action

    def pipelineStatus(self):
        return self.fields[0]['value']

    def findOrCreatePart(self, title, short=True):
        for action in self.fields:
            if action['title'] == title:
                return action

        p = { "title": title, "value": "", "short": short }
        self.fields.append(p)
        return p

    def updateBuildStageInfo(self, name, phases, info):
        url = info.get('latestExecution', {}).get('externalExecutionUrl')
        if url:
            self.findOrCreateAction('Build dashboard', url)

        si = self.findOrCreatePart(name, short=False)
        def pi(p):
            p_status = p.get('phase-status', 'IN_PROGRESS')
            return BUILD_PHASES[p_status]
        def fmt_p(p):
            msg = "{} {}".format(pi(p), p['phase-type'])
            d = p.get('duration-in-seconds')
            if d:
                return msg + " ({})".format(d)
            return msg

        def show_p(p):
            d = p.get('duration-in-seconds')
            return p['phase-type'] != 'COMPLETED' and d is None or d > 0

        def pc(p):
            ctx = p.get('phase-context', [])
            if len(ctx) > 0:
                if ctx[0] != ': ':
                    return ctx[0]
            return None

        context = [pc(p) for p in phases if pc(p)]

        if len(context) > 0:
            self.findOrCreatePart("Build Context", short=False)['value'] = " ".join(context)

        pp = [fmt_p(p) for p in phases if show_p(p)]
        si['value'] = " ".join(pp)

    def updateStatusInfo(self, stage_info, stage, status):
        stage_dict = OrderedDict()
        stage_delimiter = "\n"
        status_delimiter = " "

        if len(stage_info) > 0:
            for part in stage_info.split(stage_delimiter):
                (cur_icon, cur_stage) = part.split(status_delimiter)
                stage_dict[cur_stage] = cur_icon

        stage_dict[stage] = STATE_ICONS[status]

        part_format = '%s' + status_delimiter + '%s'
        return stage_delimiter.join([part_format % (v, k) for (k, v) in stage_dict.items()])

    def updatePipelineEvent(self, event):
        if event['detail-type'] == "CodePipeline Pipeline Execution State Change":
            state = event['detail']['state']
            self.fields[0]['value'] = state
            if state == 'STARTED':
                self.isStarted = True
            return

        if event['detail-type'] == "CodePipeline Stage Execution State Change":
            stage = event['detail']['stage']
            state = event['detail']['state']
            self.updatePipelineEventStage(stage, state)
            return

        if event['detail-type'] == "CodePipeline Action Execution State Change":
            stage = event['detail']['stage']
            state = event['detail']['state']
            self.updatePipelineEventStage(stage, state)

            action = event['detail']['action']
            provider = event['detail']['type']['provider']
            action_state = event['detail']['state']
            self.updatePipelineEventAction(action, provider, action_state)
            return

        raise ValueError('event.detail-type:' + event['detail-type'] + ' is not supported.')


    def updatePipelineEventStage(self, stage, state):
        stage_info = self.findOrCreatePart('Stages')
        stage_info['value'] = self.updateStatusInfo(stage_info['value'], stage, state)

    def updatePipelineEventAction(self, action, provider, state):
        # TODO 未実装
        logger.info("updatePipelineEventAction action={}, provider={}, state={}".format(__name__, action, provider, state))

    def color(self):
        return STATE_COLORS.get(self.pipelineStatus(), '#eee')

    def message(self):
        return [
            {
                "fields": self.fields,
                "color":  self.color(),
                "footer": self.buildInfo.executionId,
                "actions": self.actions
            }
        ]


# https://docs.aws.amazon.com/codepipeline/latest/userguide/detect-state-changes-cloudwatch-events.html    
STATE_ICONS = {
    'STARTED': ":building_construction:",
    'SUCCEEDED': ":white_check_mark:",
    'RESUMED': "",
    'FAILED': ":x:",
    'CANCELED': ":no_entry:",
    'SUPERSEDED': ""
}

STATE_COLORS = {
    'STARTED': "#9E9E9E",
    'SUCCEEDED': "good",
    'RESUMED': "",
    'FAILED': "danger",
    'CANCELED': "",
    'SUPERSEDED': ""
}

# https://docs.aws.amazon.com/codebuild/latest/APIReference/API_BuildPhase.html
BUILD_PHASES = {
    'SUCCEEDED': ":white_check_mark:",
    'FAILED': ":x:",
    'FAULT': "",
    'TIMED_OUT': ":stop_watch:",
    'IN_PROGRESS': ":building_construction:",
    'STOPPED': ""
}
