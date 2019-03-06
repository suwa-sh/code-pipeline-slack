# -*- coding: utf-8 -*-

import json
import logging
#logger = logging.getLogger()
#logger.setLevel(logging.INFO)


class CodeBuildInfo(object):
    def __init__(self, pipeline, build_id):
        self.pipeline = pipeline
        self.buildId = build_id
        self.isStarted = False

    @staticmethod
    def from_event(event):
#        logger.info(__name__)
        # logger.info(json.dumps(event, indent=2))
        # strip off leading 'codepipeline/'
        pipeline = event['detail']['additional-information']['initiator'][13:]
        bid = event['detail']['build-id']
        return CodeBuildInfo(pipeline, bid)


class BuildNotification(object):
    def __init__(self, build_info):
        self.buildInfo = build_info


class BuildInfo(object):
    def __init__(self, execution_id, pipeline, status):
        self.executionId = execution_id
        self.pipeline = pipeline
        self.revisionInfo = status
        self.isStarted = False

    def has_revision_info(self):
#        logger.info(__name__)
        return len(self.revisionInfo) > 0

    @staticmethod
    def pull_phase_info(event):
#        logger.info(__name__)
        info = event['detail']['additional-information']
        return info.get('phases')

    @staticmethod
    def from_event(event):
        if event['source'] == "aws.codepipeline":
            detail = event['detail']

#            stage = detail.get('stage', None)
#            state = detail.get('state', None)
#            logger.info("{} stage={}, state={}, detail=".format(__name__, stage, state))

            build_info = BuildInfo(detail['execution-id'], detail['pipeline'], None)
            if event['detail-type'] == "CodePipeline Pipeline Execution State Change":
                state = event['detail']['state']
                if state == 'STARTED':
                    build_info.isStarted = True
            return build_info

        # if event['source'] == "aws.codebuild":
            # logger.info(json.dumps(event, indent=2))
            # ph = BuildInfo.pull_phase_info(event)
            # logger.info(json.dumps(ph, indent=2))

        return None

    @staticmethod
    def from_message(event):
#        logger.info(__name__)
        fields = event['attachments'][0]['fields']

        execution_id = fields[0]['value']
        pipeline = fields[1]['title']
        status = fields[1]['value']

        return BuildInfo(execution_id, pipeline, status)
