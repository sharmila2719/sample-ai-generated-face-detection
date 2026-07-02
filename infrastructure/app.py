#!/usr/bin/env python3
"""CDK app entry point — AI Image Detection Pipeline."""

import aws_cdk as cdk

from stacks.pipeline_stack import PipelineStack

app = cdk.App()

PipelineStack(
    app,
    "AiImageDetectionPipeline",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1",
    ),
)

app.synth()
