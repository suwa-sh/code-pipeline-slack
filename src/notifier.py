# -*- coding: utf-8 -*-

from __future__ import print_function
from build_info import BuildInfo, CodeBuildInfo
from slack_helper import post_build_msg, find_message_for_build
from message_builder import MessageBuilder

import os
import json
import boto3
import time
import logging

LOGLEVEL = os.getenv("LOGLEVEL", "DEBUG")
if LOGLEVEL == "DEBUG":
    loglevel = logging.DEBUG
if LOGLEVEL == "INFO":
    loglevel = logging.INFO
if LOGLEVEL == "WARN":
    loglevel = logging.WARN
if LOGLEVEL == "ERROR":
    loglevel = logging.ERROR

fmt = os.getenv("LOGFORMAT", '%(asctime)s %(levelname)-5s [%(name)-24s] %(message)s - %(pathname)s %(lineno)4s')
#fmt = '%(asctime)s %(levelname)-5s [%(name)-24s] %(message)s'

logging.basicConfig(format=fmt, datefmt='%Y-%m-%d %H:%M:%S', level=loglevel)
logger = logging.getLogger()

client = boto3.client('codepipeline')


def findRevisionInfo(info):
    r = client.get_pipeline_execution(
        pipelineName=info.pipeline,
        pipelineExecutionId=info.executionId
    )['pipelineExecution']

    revs = r.get('artifactRevisions', [])
    if len(revs) > 0:
        return revs[0]
    return None


def pipelineFromBuild(codeBuildInfo):
    res = client.get_pipeline_state(name=codeBuildInfo.pipeline)

    for stage_states in res['stageStates']:
        for action_states in stage_states['actionStates']:
            execution_id = action_states.get('latestExecution', {}).get('externalExecutionId')
            if execution_id and codeBuildInfo.buildId.endswith(execution_id):
                pipeline_execution_id = stage_states['latestExecution']['pipelineExecutionId']
                return stage_states['stageName'], pipeline_execution_id, action_states

    return None, None, None


def is_skip_codepipeline_notice(event_name):
    if event_name == 'StartPipelineExecution':
        return True
    if event_name == 'PutApprovalResult':
        # TODO 一旦無視。誰が、どんなメッセージで承認、拒否したのか通知したい。
        return True
    return False


def is_skip_codebuild_notice(event_name):
    if event_name == 'StartBuild':
        return True
    if event_name == 'BatchGetBuilds':
        return True
    return False


def processCodePipeline(event):
    # logger.info("processCodePipeline")
    if is_skip_codepipeline_notice(event['detail'].get('eventName')):
        return

    build_info = BuildInfo.from_event(event)

    existing_msg = find_message_for_build(build_info)
    # logger.info("existing_msg: {}".format(existing_msg))
    builder = MessageBuilder(build_info, existing_msg)
    builder.updatePipelineEvent(event)

    if builder.needsRevisionInfo():
        revision = findRevisionInfo(build_info)
        builder.attachRevisionInfo(revision)

    post_build_msg(builder)


def processCodeBuild(event):
    # logger.info("processCodeBuild")
    if is_skip_codebuild_notice(event['detail'].get('eventName')):
        return

    cbi = CodeBuildInfo.from_event(event)
    (stage, pid, actionStates) = pipelineFromBuild(cbi)

    if not pid:
        return

    build_info = BuildInfo(pid, cbi.pipeline, actionStates)

    existing_msg = find_message_for_build(build_info)
    builder = MessageBuilder(build_info, existing_msg)

    if 'phases' in event['detail']['additional-information']:
        phases = event['detail']['additional-information']['phases']
        builder.updateBuildStageInfo(stage, phases, actionStates)

    logs = event['detail'].get('additional-information', {}).get('logs')
    if logs:
        builder.attachLogs(event['detail']['additional-information']['logs'])

    post_build_msg(builder)


def process(event):
    if event['source'] == "aws.codepipeline":
        processCodePipeline(event)
        return
    if event['source'] == "aws.codebuild":
        processCodeBuild(event)
        return
    logger.warning('event.source:' + event['source'] + ' is not supported.')



def run(event, context):
    print(json.dumps(event))
    logger.info("run")
    logger.info("{}".format(json.dumps(event)))
    # logger.info("context")
    # logger.info("{}".format(json.dumps(context, default=str)))
    process(event)


if __name__ == "__main__":
    with open ('test-event.json') as f:
        events = json.load(f)
        for e in events:
            run(e, {})
            time.sleep(1)
