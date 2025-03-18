from collections.asb import Mapping, Sequence

import aws_cdk as cdk
from constructs import Construct

class lambda_function(cdk.aws_lambda_python_alpha.PythonFunction):
    def __init__(
        self,
        scope: Construct,
        id: str,
        *,
        function_name: str | None = None,
        description: str | None = None,
        memory: int | None = None,
        ephemeral_storage: int | None = None,
        enviroment: dict[str, str] | None = None,
        permissions: Sequence[cdk.aws_iam.PolicyStatement | cdk.aws_iam.IManagedPolicy] | None = None,
        timeout: cdk.Duration | None = None,
        events: Sequence[cdk.aws_lambda.IEventSource] | None = None,
        on_failure: cdk.aws_sns.Topic | None = None,

    ) -> None:
        super().__init__(
            scope,
            id,
            entry=str
        )
