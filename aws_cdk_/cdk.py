from pathlib import Path
from collections.abc import Mapping, Sequence
from typing import final

import aws_cdk as cdk
import aws_cdk.aws_lambda_python_alpha as lambda_python
import aws_cdk.aws_scheduler_alpha as schedule
import aws_cdk.aws_scheduler_targets_alpha as schedule_targets
import aws_cdk.aws_glue_alpha as glue
from constructs import Construct


class lambda_function(lambda_python.PythonFunction):
    def __init__(
        self,
        scope: Construct,
        id: str,
        entry: Path,
        *,
        function_name: str | None = None,
        description: str | None = None,
        memory: int | None = None,
        ephemeral_storage: int | None = None,
        enviroment: dict[str, str] | None = None,
        permissions: Sequence[cdk.aws_iam.PolicyStatement | cdk.aws_iam.IManagedPolicy]
        | None = None,
        timeout: cdk.Duration | None = None,
        events: Sequence[cdk.aws_lambda.IEventSource] | None = None,
        on_failure: cdk.aws_sns.Topic | None = None,
        vpc: cdk.aws_ec2.IVpc | None = None,
        vpc_subnets: cdk.aws_ec2.SubnetSelection | None = None,
        vpc_security_groups: Sequence[cdk.aws_ec2.ISecurityGroup] | None = None,
    ) -> None:
        super().__init__(
            scope,
            id,
            entry=str(entry),
            runtime=cdk.aws_lambda.Runtime.PYTHON_3_12,  # pyright: ignore[reportArgumentType]
            index="function.py",
            handler="handler",
            bundling=lambda_python.BundlingOptions(asset_excludes=[".venv"]),
            function_name=function_name,
            description=description,
            memory_size=memory,
            ephemeral_storage_size=cdk.Size.mebibytes(ephemeral_storage)
            if ephemeral_storage is not None
            else None,
            environment=enviroment,
            initial_policy=[
                p for p in permissions if isinstance(p, cdk.aws_iam.PolicyStatement)
            ]
            if permissions is not None
            else None,
            timeout=timeout,
            events=events,
            on_failure=cdk.aws_lambda_destinations.SnsDestination(on_failure)  # pyright: ignore[reportArgumentType]
            if on_failure is not None
            else None,
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            security_groups=vpc_security_groups,
        )

        if permissions is not None:
            for p in permissions:
                if not isinstance(p, cdk.aws_iam.PolicyStatement):
                    self.role.add_managed_policy(p)  # pyright: ignore


@final
class schedule_lambda_funtion(Construct):
    def __init__(
        self,
        scope: Construct,
        id: str,
        entry: Path,
        *,
        cron: str,
        function_name: str | None = None,
        description: str | None = None,
        memory: int | None = None,
        ephemeral_storage: int | None = None,
        enviroment: dict[str, str] | None = None,
        permissions: Sequence[cdk.aws_iam.PolicyStatement | cdk.aws_iam.IManagedPolicy]
        | None = None,
        input_: dict[str, str | int] | None = None,
        timeout: cdk.Duration | None = None,
        on_failure: cdk.aws_sns.Topic | None = None,
        vpc: cdk.aws_ec2.IVpc | None = None,
        vpc_subnets: cdk.aws_ec2.SubnetSelection | None = None,
        vpc_security_groups: Sequence[cdk.aws_ec2.ISecurityGroup] | None = None,
    ) -> None:
        super().__init__(scope, id)
        base_id = id

        self.function = lambda_function(
            self,
            f"{base_id}-function",
            entry=entry,
            function_name=function_name,
            description=description,
            memory=memory,
            ephemeral_storage=ephemeral_storage,
            enviroment=enviroment,
            permissions=permissions,
            timeout=timeout,
            on_failure=on_failure,
            vpc=vpc,
            vpc_subnets=vpc_subnets,
            vpc_security_groups=vpc_security_groups,
        )
        self.schedule = schedule.Schedule(
            self,
            f"{base_id}-schedule",
            schedule=schedule.ScheduleExpression.expression(
                expression=f"cron({cron})",
                time_zone=cdk.TimeZone.EUROPE_MADRID,  # pyright: ignore[reportArgumentType]
            ),
            target=schedule_targets.LambdaInvoke(
                self.function,  # pyright: ignore[reportArgumentType]
                input=schedule.ScheduleTargetInput.from_object(input_)
                if input_ is not None
                else None,
            ),
        )


@final
class spark_glue_job(glue.PySparkEtlJob):
    DEFAULT_MANAGED_POLICIES = (
        cdk.aws_iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
        cdk.aws_iam.ManagedPolicy.from_aws_managed_policy_name(
            "service-role/AWSGlueServiceRole"
        ),
    )

    def __init__(
        self,
        scope: Construct,
        id: str,
        STACK_PATH: Path,
        *,
        job_name: str | None = None,
        description: str | None = None,
        max_concurrency: int | None = None,
        permissions: Sequence[cdk.aws_iam.PolicyStatement | cdk.aws_iam.IManagedPolicy]
        | None = None,
        default_arguments: Mapping[str, str] | None = None,
        extra_jars: Sequence[glue.Code] | None = None,
    ) -> None:
        role = cdk.aws_iam.Role(
            scope,
            f"{id}-role",
            assumed_by=cdk.aws_iam.ServicePrincipal("glue.amazonaws.com"),
        )
        for p in self.DEFAULT_MANAGED_POLICIES:
            role.add_managed_policy(p)
        if permissions is not None:
            for p in permissions:
                if isinstance(p, cdk.aws_iam.PolicyStatement):
                    _ = role.add_to_policy(p)
                else:
                    role.add_managed_policy(p)

        super().__init__(
            scope,
            id,
            job_name=job_name,
            description=description,
            script=glue.Code.from_asset(
                str((STACK_PATH / "glue" / id).with_suffix(".py"))
            ),
            glue_version=glue.GlueVersion.V5_0,
            role=role,
            extra_jars=extra_jars,
            max_concurrent_runs=max_concurrency,
            default_arguments=default_arguments,
            enable_profiling_metrics=False,
        )
