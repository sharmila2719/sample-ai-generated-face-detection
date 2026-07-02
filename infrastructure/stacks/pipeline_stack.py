"""CDK stack: AI Image Detection Pipeline.

Resources:
  - S3 intake bucket + static web UI bucket
  - DynamoDB: detection results (with content-hash GSI), rate limits
  - SNS topic: detection alerts
  - KMS key: C2PA verification (ECC_NIST_P256, retained for historical verification)
  - Lambda: detect, health, s3-event, upload-url, session-check, Lambda@Edge auth
  - API Gateway REST API
  - CloudFront distribution
  - CloudWatch alarms
"""

import os

from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigw,
    aws_cloudwatch as cw,
    aws_cloudwatch_actions as cw_actions,
    aws_dynamodb as ddb,
    aws_iam as iam,
    aws_kms as kms,
    aws_lambda as _lambda,
    aws_logs as logs,
    aws_s3 as s3,
    aws_s3_notifications as s3n,
    aws_sns as sns,
)
from constructs import Construct


class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        # ── SNS Alerts topic ──────────────────────────────────────────
        alerts_topic = sns.Topic(
            self, "DetectionAlerts",
            topic_name="ai-detection-alerts",
            display_name="AI Detection Alerts",
        )

        # ── S3 intake bucket ──────────────────────────────────────────
        intake_bucket = s3.Bucket(
            self, "IntakeBucket",
            bucket_name=f"ai-images-to-analyze-{self.account}-{self.region}",
            encryption=s3.BucketEncryption.S3_MANAGED,
            enforce_ssl=True,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            cors=[
                s3.CorsRule(
                    allowed_methods=[s3.HttpMethods.PUT],
                    allowed_origins=["*"],
                    allowed_headers=["*"],
                    exposed_headers=["ETag"],
                    max_age=300,
                )
            ],
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ── DynamoDB tables ───────────────────────────────────────────
        detection_table = ddb.Table(
            self, "DetectionResultsTable",
            table_name="ai-detection-results",
            partition_key=ddb.Attribute(name="image_id", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="tenant_id", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            point_in_time_recovery=True,
            encryption=ddb.TableEncryption.AWS_MANAGED,
            removal_policy=RemovalPolicy.RETAIN,
        )
        detection_table.add_global_secondary_index(
            index_name="by-tenant-content-hash",
            partition_key=ddb.Attribute(name="content_hash_pk", type=ddb.AttributeType.STRING),
            sort_key=ddb.Attribute(name="detection_timestamp", type=ddb.AttributeType.STRING),
            projection_type=ddb.ProjectionType.ALL,
        )

        rate_limit_table = ddb.Table(
            self, "RateLimitTable",
            table_name="generation-rate-limits",
            partition_key=ddb.Attribute(name="rate_pk", type=ddb.AttributeType.STRING),
            billing_mode=ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=RemovalPolicy.RETAIN,
        )

        # ── KMS key (C2PA verification, asymmetric ECC) ───────────────
        signing_key = kms.Key(
            self, "C2paSigningKey",
            alias="alias/ai-image-c2pa-signing",
            key_spec=kms.KeySpec.ECC_NIST_P256,
            key_usage=kms.KeyUsage.SIGN_VERIFY,
            removal_policy=RemovalPolicy.RETAIN,
            description="Asymmetric key for historical C2PA manifest verification.",
        )

        # ── Common Lambda environment ─────────────────────────────────
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        lambda_asset_dir = os.path.join(repo_root, "build", "lambda_asset")
        _build_lambda_asset(repo_root, lambda_asset_dir)
        lambda_code = _lambda.Code.from_asset(lambda_asset_dir)

        common_env = {
            "AWS_REGION_OVERRIDE": self.region,
            "SAGEMAKER_ENDPOINT_NAME": "ai-image-detector",
            "S3_INTAKE_BUCKET_NAME": intake_bucket.bucket_name,
            "DYNAMODB_DETECTION_TABLE": detection_table.table_name,
            "DYNAMODB_RATE_LIMIT_TABLE": rate_limit_table.table_name,
            "SNS_TOPIC_ARN": alerts_topic.topic_arn,
            "KMS_SIGNING_KEY_ARN": signing_key.key_arn,
            "LOG_LEVEL": "INFO",
            "BEDROCK_GUARDRAIL_ID": "REPLACE_ME",
            "USE_AGENT": "true",
            "BEDROCK_REGION": "eu-west-1",
        }

        # ── Detection Lambda ──────────────────────────────────────────
        detection_lambda = _lambda.Function(
            self, "DetectionLambda",
            function_name="ai-image-detection",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            handler="lambda_handlers.detection_handler.lambda_handler",
            code=lambda_code,
            memory_size=3008,
            timeout=Duration.seconds(60),
            environment=common_env,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_YEAR,
        )

        # ── Health Lambda ─────────────────────────────────────────────
        health_lambda = _lambda.Function(
            self, "HealthLambda",
            function_name="ai-image-health",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            handler="lambda_handlers.health_handler.lambda_handler",
            code=lambda_code,
            memory_size=512,
            timeout=Duration.seconds(10),
            environment=common_env,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_MONTH,
        )

        # ── S3-event Lambda ───────────────────────────────────────────
        s3_event_lambda = _lambda.Function(
            self, "S3EventLambda",
            function_name="ai-image-s3-event",
            runtime=_lambda.Runtime.PYTHON_3_12,
            architecture=_lambda.Architecture.X86_64,
            handler="lambda_handlers.s3_event_handler.lambda_handler",
            code=lambda_code,
            memory_size=3008,
            timeout=Duration.seconds(60),
            environment=common_env,
            tracing=_lambda.Tracing.ACTIVE,
            log_retention=logs.RetentionDays.ONE_YEAR,
        )

        # ── IAM policies ──────────────────────────────────────────────
        sagemaker_policy = iam.PolicyStatement(
            actions=["sagemaker:InvokeEndpoint"],
            resources=[
                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/ai-image-detector",
                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/ai-composite-specialist",
                f"arn:aws:sagemaker:{self.region}:{self.account}:endpoint/ai-aigc-ensemble",
            ],
        )
        bedrock_guardrail_policy = iam.PolicyStatement(
            sid="InvokeBedrockGuardrailOnly",
            actions=["bedrock:ApplyGuardrail"],
            resources=["*"],
        )

        for fn in [detection_lambda, s3_event_lambda]:
            fn.add_to_role_policy(sagemaker_policy)
            fn.add_to_role_policy(bedrock_guardrail_policy)
            signing_key.grant(fn, "kms:Verify", "kms:GetPublicKey")
            intake_bucket.grant_read(fn)
            detection_table.grant_read_write_data(fn)
            rate_limit_table.grant_read_write_data(fn)
            alerts_topic.grant_publish(fn)
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["rekognition:RecognizeCelebrities", "rekognition:DetectFaces",
                             "rekognition:DetectLabels"],
                    resources=["*"],
                )
            )
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                    resources=["*"],
                )
            )

        health_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:ListFoundationModels",
                    "rekognition:ListCollections",
                    "sagemaker:DescribeEndpoint",
                    "dynamodb:DescribeTable",
                    "sns:GetTopicAttributes",
                ],
                resources=["*"],
            )
        )

        # ── S3 event notification ─────────────────────────────────────
        intake_bucket.add_event_notification(
            s3.EventType.OBJECT_CREATED,
            s3n.LambdaDestination(s3_event_lambda),
        )

        # ── API Gateway ───────────────────────────────────────────────
        api = apigw.RestApi(
            self, "PipelineApi",
            rest_api_name="ai-image-pipeline",
            deploy_options=apigw.StageOptions(
                tracing_enabled=True,
                logging_level=apigw.MethodLoggingLevel.INFO,
                metrics_enabled=True,
            ),
        )
        api_root = api.root.add_resource("api")

        detect_integration = apigw.LambdaIntegration(detection_lambda, timeout=Duration.seconds(29))
        detect_res = api_root.add_resource("detect")
        detect_res.add_method("POST", detect_integration, authorization_type=apigw.AuthorizationType.NONE)
        batch_res = detect_res.add_resource("batch")
        batch_res.add_method("POST", detect_integration, authorization_type=apigw.AuthorizationType.NONE)

        health_res = api.root.add_resource("health")
        health_res.add_method(
            "GET",
            apigw.LambdaIntegration(health_lambda),
            authorization_type=apigw.AuthorizationType.NONE,
        )

        # ── CloudWatch alarms ─────────────────────────────────────────
        _latency_alarm(self, "DetectionLatencyHigh", detection_lambda, 25_000, alerts_topic)
        _error_alarm(self, "DetectionErrors", detection_lambda, alerts_topic)
        _error_alarm(self, "S3EventErrors", s3_event_lambda, alerts_topic)

        # ── Web UI ────────────────────────────────────────────────────
        self.alerts_topic = alerts_topic
        _build_web_ui(
            stack=self, api=api, intake_bucket=intake_bucket,
            lambda_code=lambda_code, common_env=common_env,
            detection_lambda=detection_lambda, health_lambda=health_lambda,
        )

        # ── Outputs ───────────────────────────────────────────────────
        CfnOutput(self, "ApiEndpoint", value=api.url)
        CfnOutput(self, "IntakeBucketName", value=intake_bucket.bucket_name)
        CfnOutput(self, "AlertsTopicArn", value=alerts_topic.topic_arn)
        CfnOutput(self, "SigningKeyArn", value=signing_key.key_arn)


# ── Helpers ───────────────────────────────────────────────────────────────

def _latency_alarm(scope, id_: str, fn, threshold_ms: int, topic):
    alarm = cw.Alarm(
        scope, id_,
        metric=fn.metric_duration(statistic="p95", period=Duration.minutes(5)),
        threshold=threshold_ms,
        evaluation_periods=2,
        treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        comparison_operator=cw.ComparisonOperator.GREATER_THAN_THRESHOLD,
    )
    alarm.add_alarm_action(cw_actions.SnsAction(topic))


def _error_alarm(scope, id_: str, fn, topic):
    alarm = cw.Alarm(
        scope, id_,
        metric=fn.metric_errors(period=Duration.minutes(5)),
        threshold=5,
        evaluation_periods=1,
        treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
    )
    alarm.add_alarm_action(cw_actions.SnsAction(topic))


def _build_lambda_asset(repo_root: str, target_dir: str) -> None:
    """Stage Lambda source files for CDK packaging."""
    import shutil
    import subprocess
    import sys

    requirements = os.path.join(repo_root, "infrastructure", "lambda_requirements.txt")
    marker = os.path.join(target_dir, ".build_complete")

    def _newest_mtime() -> float:
        newest = os.path.getmtime(requirements) if os.path.exists(requirements) else 0.0
        for tree in ("src", "lambda_handlers"):
            tree_path = os.path.join(repo_root, tree)
            if not os.path.isdir(tree_path):
                continue
            for root, _dirs, files in os.walk(tree_path):
                if "__pycache__" in root:
                    continue
                for fname in files:
                    if fname.endswith((".pyc", ".pyo")):
                        continue
                    try:
                        newest = max(newest, os.path.getmtime(os.path.join(root, fname)))
                    except OSError:
                        continue
        return newest

    if os.path.isfile(marker):
        try:
            if os.path.getmtime(marker) >= _newest_mtime():
                return
        except OSError:
            pass

    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    for name in ("src", "lambda_handlers"):
        src = os.path.join(repo_root, name)
        if os.path.isdir(src):
            shutil.copytree(
                src, os.path.join(target_dir, name),
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"),
            )

    if os.path.exists(requirements):
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "--platform", "manylinux2014_x86_64",
            "--target", target_dir,
            "--implementation", "cp",
            "--python-version", "3.12",
            "--only-binary=:all:",
            "--upgrade",
            "-r", requirements,
        ])

    with open(marker, "w") as f:
        f.write("ok\n")


def _build_web_ui(stack, api, intake_bucket, lambda_code, common_env,
                  detection_lambda, health_lambda):
    """Add upload-url Lambda, session-check Lambda, CloudFront + S3 static site."""
    from aws_cdk import (
        Duration, RemovalPolicy, CfnOutput,
        aws_apigateway as apigw,
        aws_cloudfront as cloudfront,
        aws_cloudfront_origins as origins,
        aws_iam as iam,
        aws_lambda as _lambda,
        aws_logs as logs,
        aws_s3 as s3,
        aws_s3_deployment as s3deploy,
    )

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    # Upload-URL Lambda
    upload_lambda = _lambda.Function(
        stack, "UploadUrlLambda",
        function_name="ai-image-upload-url",
        runtime=_lambda.Runtime.PYTHON_3_12,
        architecture=_lambda.Architecture.X86_64,
        handler="lambda_handlers.upload_url_handler.lambda_handler",
        code=lambda_code,
        memory_size=512,
        timeout=Duration.seconds(10),
        environment=common_env,
        tracing=_lambda.Tracing.ACTIVE,
        log_retention=logs.RetentionDays.ONE_MONTH,
    )
    intake_bucket.grant_put(upload_lambda)

    api_root = api.root.get_resource("api") or api.root.add_resource("api")
    cors_opts = apigw.CorsOptions(
        allow_origins=apigw.Cors.ALL_ORIGINS,
        allow_methods=["POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Tenant-ID", "X-Request-ID"],
        max_age=Duration.minutes(5),
    )
    upload_res = api_root.add_resource("upload-url", default_cors_preflight_options=cors_opts)
    upload_res.add_method("POST", apigw.LambdaIntegration(upload_lambda), authorization_type=apigw.AuthorizationType.NONE)

    # Session-check Lambda
    secret_id = "sample-ai-generated-face-detection/web-ui-password"
    secret_arn_pattern = (
        f"arn:aws:secretsmanager:{stack.region}:{stack.account}"
        f":secret:{secret_id}-??????"
    )
    session_env = dict(common_env)
    session_env["WEB_UI_PASSWORD_SECRET_ARN"] = secret_id

    session_check_lambda = _lambda.Function(
        stack, "SessionCheckLambda",
        function_name="ai-image-webui-session-check",
        runtime=_lambda.Runtime.PYTHON_3_12,
        architecture=_lambda.Architecture.X86_64,
        handler="lambda_handlers.session_check_handler.lambda_handler",
        code=lambda_code,
        memory_size=256,
        timeout=Duration.seconds(5),
        environment=session_env,
        tracing=_lambda.Tracing.ACTIVE,
        log_retention=logs.RetentionDays.ONE_MONTH,
    )
    session_check_lambda.add_to_role_policy(
        iam.PolicyStatement(
            sid="ReadWebUiPasswordSecret",
            actions=["secretsmanager:GetSecretValue"],
            resources=[secret_arn_pattern],
        )
    )

    session_res = api_root.add_resource("session-check", default_cors_preflight_options=cors_opts)
    session_res.add_method("POST", apigw.LambdaIntegration(session_check_lambda), authorization_type=apigw.AuthorizationType.NONE)

    # Static site bucket
    site_bucket = s3.Bucket(
        stack, "WebSiteBucket",
        bucket_name=f"ai-image-webui-{stack.account}-{stack.region}",
        encryption=s3.BucketEncryption.S3_MANAGED,
        enforce_ssl=True,
        block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
        removal_policy=RemovalPolicy.RETAIN,
    )

    # CloudFront distribution
    origin = origins.S3BucketOrigin.with_origin_access_control(site_bucket)
    distribution = cloudfront.Distribution(
        stack, "WebDistribution",
        default_root_object="index.html",
        default_behavior=cloudfront.BehaviorOptions(
            origin=origin,
            viewer_protocol_policy=cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
            cache_policy=cloudfront.CachePolicy.CACHING_DISABLED,
        ),
    )

    # Deploy web files
    api_url = api.url.rstrip("/") if hasattr(api.url, "rstrip") else api.url
    config_js = f'window.APP_CONFIG = {{"apiBase":"{api_url}","tenantId":"web-demo"}};\n'
    s3deploy.BucketDeployment(
        stack, "WebSiteDeploy",
        sources=[
            s3deploy.Source.asset(os.path.join(repo_root, "web")),
            s3deploy.Source.data("config.js", config_js),
        ],
        destination_bucket=site_bucket,
        distribution=distribution,
        distribution_paths=["/*"],
    )

    CfnOutput(stack, "WebUiUrl", value=f"https://{distribution.distribution_domain_name}/")
    CfnOutput(stack, "WebUiBucket", value=site_bucket.bucket_name)
