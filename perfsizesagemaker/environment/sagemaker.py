import boto3
from botocore.exceptions import ClientError
import logging.config
from perfsize.perfsize import Config, EnvironmentManager
from perfsizesagemaker.constants import Parameter
from perfsizesagemaker.credentials import CredentialsManager
from typing import Optional
import yaml

log = logging.getLogger(__name__)

# AWS Account access:

# https://boto3.amazonaws.com/v1/documentation/api/latest/guide/configuration.html
# See this page for details on how configuration values are looked up via a
# Config object, environment variables, and the ~/.aws/config file. Probably
# will be relying on environment variables AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
# AWS_SESSION_TOKEN for the given role.

# Permissions:
# Option 1: For a full Amazon SageMaker access, search and attach the AmazonSageMakerFullAccess policy.
# Option 2: For granting a limited access to an IAM role, paste the following Action elements manually into the JSON file of the IAM role: "Action": ["sagemaker:CreateEndpoint", "sagemaker:CreateEndpointConfig"] "Resource": [ "arn:aws:sagemaker:region:account-id:endpoint/endpointName" "arn:aws:sagemaker:region:account-id:endpoint-config/endpointConfigName" ]


# Simplified representation of SageMaker endpoint and several dependencies:
# subset of fields from Endpoint, EndpointConfig, ScalableTarget, ScalingPolicy.
#
# Current implementation assumes:
# - Each Endpoint has exactly one EndpointConfig.
# - Each Endpoint has exactly one ProductionVariant.
# - Each EndpointConfig has exactly one ProductionVariant.
# - TODO: implement autoscaling
# - Each Endpoint has at most one ScalableTarget and at most one ScalingPolicy.
# - ScalableTarget would define a DesiredInstanceCount with a min and max.
# - ScalingPolicy would be based on SageMakerVariantInvocationsPerInstance.
# - Only checking these fields for expected state when comparing and deciding
#   whether an update is needed. All other fields should be default.
class EndpointConfig:
    def __init__(
        self,
        endpoint_config_name: str,
        model_name: str,
        instance_type: str,
        initial_instance_count: int,
    ):
        self.endpoint_config_name = endpoint_config_name
        self.model_name = model_name
        self.instance_type = instance_type
        self.initial_instance_count = initial_instance_count


class CombinedStatus:
    def __init__(
        self,
        endpoint_name: str,
        endpoint_status: str,
        endpoint_config_name: Optional[str] = None,
        model_name: Optional[str] = None,
        instance_type: Optional[str] = None,
        initial_instance_count: Optional[int] = None,
        current_instance_count: Optional[int] = None,
        desired_instance_count: Optional[int] = None,
        scaling_enabled: Optional[bool] = None,
        scaling_min_instance_count: Optional[int] = None,
        scaling_max_instance_count: Optional[int] = None,
        scaling_metric: Optional[str] = None,
        scaling_target: Optional[int] = None,
    ):
        self.endpoint_name = endpoint_name
        self.endpoint_status = endpoint_status
        self.endpoint_config_name = endpoint_config_name
        self.model_name = model_name
        self.instance_type = instance_type
        self.initial_instance_count = initial_instance_count
        self.current_instance_count = current_instance_count
        self.desired_instance_count = desired_instance_count
        self.scaling_enabled = scaling_enabled
        self.scaling_min_instance_count = scaling_min_instance_count
        self.scaling_max_instance_count = scaling_max_instance_count
        self.scaling_metric = scaling_metric
        self.scaling_target = scaling_target

    def __repr__(self) -> str:
        return (
            f"CombinedStatus("
            f"endpoint_name={self.endpoint_name}, "
            f"endpoint_status={self.endpoint_status}, "
            f"endpoint_config_name={self.endpoint_config_name}, "
            f"model_name={self.model_name}, "
            f"instance_type={self.instance_type}, "
            f"initial_instance_count={self.initial_instance_count}, "
            f"current_instance_count={self.current_instance_count}, "
            f"desired_instance_count={self.desired_instance_count}, "
            f"scaling_enabled={self.scaling_enabled}, "
            f"scaling_min_instance_count={self.scaling_min_instance_count}, "
            f"scaling_max_instance_count={self.scaling_max_instance_count}, "
            f"scaling_metric={self.scaling_metric}, "
            f"scaling_target={self.scaling_target}"
            f")"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, CombinedStatus):
            return NotImplemented
        return (
            self.endpoint_name == other.endpoint_name
            and self.endpoint_status == other.endpoint_status
            and self.endpoint_config_name == other.endpoint_config_name
            and self.model_name == other.model_name
            and self.instance_type == other.instance_type
            and self.initial_instance_count == other.initial_instance_count
            and self.current_instance_count == other.current_instance_count
            and self.desired_instance_count == other.desired_instance_count
            and self.scaling_enabled == other.scaling_enabled
            and self.scaling_min_instance_count == other.scaling_min_instance_count
            and self.scaling_max_instance_count == other.scaling_max_instance_count
            and self.scaling_metric == other.scaling_metric
            and self.scaling_target == other.scaling_target
        )


class SageMakerEnvironmentManager(EnvironmentManager):
    def __init__(
        self, iam_role_arn: Optional[str] = None, region: Optional[str] = None,
    ):
        self.credentials_manager = CredentialsManager(iam_role_arn, region)
        self.region = region

    def _sagemaker_client(self) -> boto3.session.Session.client:
        (
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        ) = self.credentials_manager.refresh()
        return boto3.client(
            service_name="sagemaker",
            region_name=self.region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )

    def get_endpoint_config(
        self, endpoint_config_name: str
    ) -> Optional[EndpointConfig]:
        client = self._sagemaker_client()
        try:
            response = client.describe_endpoint_config(
                EndpointConfigName=endpoint_config_name
            )
        except ClientError as err:
            if err.args and "Could not find endpoint configuration" in err.args[0]:
                log.debug(f"EndpointConfig {endpoint_config_name} not found.")
                return None
            else:
                raise err
        assert response["EndpointConfigName"] == endpoint_config_name
        assert len(response["ProductionVariants"]) == 1
        variant = response["ProductionVariants"][0]
        model_name = variant["ModelName"]
        instance_type = variant["InstanceType"]
        initial_instance_count = variant["InitialInstanceCount"]
        return EndpointConfig(
            endpoint_config_name=endpoint_config_name,
            model_name=model_name,
            instance_type=instance_type,
            initial_instance_count=initial_instance_count,
        )

    def get_status(self, endpoint_name: str) -> CombinedStatus:
        # Check Endpoint
        client = self._sagemaker_client()
        try:
            response = client.describe_endpoint(EndpointName=endpoint_name)
        except ClientError as err:
            if err.args and "Could not find endpoint" in err.args[0]:
                return CombinedStatus(
                    endpoint_name=endpoint_name, endpoint_status="NotFound",
                )
            else:
                raise (err)
        log.debug(f"Endpoint {endpoint_name} has description {response}")
        assert response["EndpointName"] == endpoint_name
        endpoint_config_name = response["EndpointConfigName"]
        current_instance_count = None
        desired_instance_count = None
        if "ProductionVariants" in response:
            # Some states like "Creating" do not have ProductionVariants yet
            assert len(response["ProductionVariants"]) == 1
            variant = response["ProductionVariants"][0]
            current_instance_count = variant["CurrentInstanceCount"]
            desired_instance_count = variant["DesiredInstanceCount"]
        endpoint_status = response["EndpointStatus"]

        # Check EndpointConfig
        endpoint_config = self.get_endpoint_config(endpoint_config_name)
        if endpoint_config is None:
            raise RuntimeError(
                f"Endpoint {endpoint_name} is pointing to EndpointConfig {endpoint_config_name}, but the config cannot be found."
            )

        return CombinedStatus(
            endpoint_name=endpoint_name,
            endpoint_status=endpoint_status,
            endpoint_config_name=endpoint_config_name,
            model_name=endpoint_config.model_name,
            instance_type=endpoint_config.instance_type,
            initial_instance_count=endpoint_config.initial_instance_count,
            current_instance_count=current_instance_count,
            desired_instance_count=desired_instance_count,
            # TODO: Not implemented yet...
            # scaling_enabled=scaling_enabled,
            # scaling_min_instance_count=scaling_min_instance_count,
            # scaling_max_instance_count=scaling_max_instance_count,
            # scaling_metric=scaling_metric,
            # scaling_target=scaling_target,
        )

    def wait_endpoint_deleted(self, endpoint_name: str) -> None:
        log.debug(f"About to wait for Endpoint {endpoint_name} to be deleted...")
        client = self._sagemaker_client()
        waiter = client.get_waiter("endpoint_deleted")
        waiter.wait(
            EndpointName=endpoint_name, WaiterConfig={"Delay": 30, "MaxAttempts": 60}
        )
        log.debug(f"Endpoint {endpoint_name} should be deleted now")

    def delete_endpoint(self, endpoint_name: str) -> None:
        log.debug(f"About to delete Endpoint {endpoint_name}...")
        client = self._sagemaker_client()
        response = client.delete_endpoint(EndpointName=endpoint_name)
        log.debug(f"Endpoint {endpoint_name} delete response {response}")
        self.wait_endpoint_deleted(endpoint_name)

    def wait_endpoint_in_service(self, endpoint_name: str) -> None:
        log.debug(f"About to wait for Endpoint {endpoint_name} to be InService")
        client = self._sagemaker_client()
        waiter = client.get_waiter("endpoint_in_service")
        waiter.wait(
            EndpointName=endpoint_name, WaiterConfig={"Delay": 30, "MaxAttempts": 120}
        )
        log.debug(f"Endpoint {endpoint_name} should be InService now")

    def delete_endpoint_config(self, endpoint_config_name: str) -> None:
        log.debug(f"About to delete EndpointConfig {endpoint_config_name}...")
        client = self._sagemaker_client()
        response = client.delete_endpoint_config(
            EndpointConfigName=endpoint_config_name
        )
        log.debug(f"EndpointConfig {endpoint_config_name} delete response {response}")

    def create_endpoint_config(
        self,
        endpoint_config_name: str,
        model_name: str,
        initial_instance_count: int,
        instance_type: str,
    ) -> None:
        client = self._sagemaker_client()
        response = client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    "VariantName": "variant-name-1",
                    "ModelName": model_name,
                    "InitialInstanceCount": initial_instance_count,
                    "InstanceType": instance_type,
                },
            ],
        )
        log.debug(f"EndpointConfig {endpoint_config_name} creation response {response}")

    # create_endpoint()
    # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/sagemaker.html#SageMaker.Client.create_endpoint
    # You must not delete an EndpointConfig that is in use by an endpoint or while
    # the UpdateEndpoint or CreateEndpoint operations are being performed.
    # To update an endpoint, you must create a new EndpointConfig .
    # Call DescribeEndpointConfig before calling CreateEndpoint to minimize the
    # potential impact of an eventually consistent read.
    # To check the status of an endpoint, use the DescribeEndpoint API.
    def create_endpoint(self, endpoint_name: str, endpoint_config_name: str) -> None:
        endpoint_config = self.get_endpoint_config(endpoint_config_name)
        if endpoint_config is None:
            raise RuntimeError(
                f"Endpoint {endpoint_name} cannot be created if EndpointConfig {endpoint_config_name} is not found."
            )

        client = self._sagemaker_client()
        response = client.create_endpoint(
            EndpointName=endpoint_name, EndpointConfigName=endpoint_config_name,
        )
        log.debug(f"Endpoint {endpoint_name} creation response {response}")
        self.wait_endpoint_in_service(endpoint_name)

    def teardown(self, config: Config) -> None:
        endpoint_name = config.parameters[Parameter.endpoint_name]
        endpoint_config_name = config.parameters[Parameter.endpoint_config_name]

        status = self.get_status(endpoint_name)
        endpoint_status = status.endpoint_status
        if (
            endpoint_status == "OutOfService"
            or endpoint_status == "InService"
            or endpoint_status == "Failed"
        ):
            log.info(
                f"Endpoint {endpoint_name} is {endpoint_status}. "
                f"About to delete endpoint..."
            )
            self.delete_endpoint(endpoint_name)
        elif (
            endpoint_status == "Creating"
            or endpoint_status == "Updating"
            or endpoint_status == "SystemUpdating"
            or endpoint_status == "RollingBack"
        ):
            log.warning(
                f"Endpoint {endpoint_name} is {endpoint_status}. "
                f"Check if other processes are interfering. "
                f"Will try to wait and delete..."
            )
            self.wait_endpoint_in_service(endpoint_name)
            self.delete_endpoint(endpoint_name)
        elif endpoint_status == "Deleting":
            log.warning(
                f"Endpoint {endpoint_name} is already Deleting. "
                f"Check if other processes are interfering. "
                f"Will try to wait for deletion..."
            )
            self.wait_endpoint_deleted(endpoint_name)
        elif endpoint_status == "NotFound":
            log.info(f"Endpoint {endpoint_name} not found.")
        else:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} has unrecognized status "
                f"{endpoint_status}"
            )

        # TODO: Check if an endpoint config is being used by any endpoint
        # Currently assuming given endpoint config is not being used elsewhere.

        endpoint_config = self.get_endpoint_config(endpoint_config_name)
        if endpoint_config:
            log.info(
                f"EndpointConfig {endpoint_config_name} found. "
                f"About to delete it..."
            )
            self.delete_endpoint_config(endpoint_config_name)
            log.info(f"EndpointConfig {endpoint_config_name} deleted.")
        else:
            log.info(f"EndpointConfig {endpoint_config_name} not found.")

    def setup(self, config: Config) -> None:
        endpoint_name = config.parameters[Parameter.endpoint_name]
        endpoint_config_name = config.parameters[Parameter.endpoint_config_name]
        model_name = config.parameters[Parameter.model_name]
        instance_type = config.parameters[Parameter.instance_type]
        initial_instance_count = int(
            config.parameters[Parameter.initial_instance_count]
        )

        # Check if current state already set correctly
        expected = CombinedStatus(
            endpoint_name=endpoint_name,
            endpoint_status="InService",
            endpoint_config_name=endpoint_config_name,
            model_name=model_name,
            instance_type=instance_type,
            initial_instance_count=initial_instance_count,
            current_instance_count=initial_instance_count,
            desired_instance_count=initial_instance_count,
            scaling_enabled=None,
            scaling_min_instance_count=None,
            scaling_max_instance_count=None,
            scaling_metric=None,
            scaling_target=None,
        )
        actual = self.get_status(endpoint_name)
        if actual == expected:
            log.info(f"No environment update needed: {actual}")
            return

        self.teardown(config)
        self.create_endpoint_config(
            endpoint_config_name=endpoint_config_name,
            model_name=model_name,
            initial_instance_count=initial_instance_count,
            instance_type=instance_type,
        )
        self.create_endpoint(
            endpoint_name=endpoint_name, endpoint_config_name=endpoint_config_name
        )
        actual = self.get_status(endpoint_name)
        assert actual == expected

        # TODO: Add option to do a configurable warmup run when endpoint changes


if __name__ == "__main__":
    with open("logging.yml", "r") as stream:
        log_config = yaml.safe_load(stream)
    logging.config.dictConfig(log_config)
    for name in logging.root.manager.loggerDict:  # type: ignore
        if name.startswith("perfsize"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    # TODO: move below to tests

    endpoint_name = "LEARNING-model-sim-public-1"
    config = Config(
        parameters={
            Parameter.host: "runtime.sagemaker.us-west-2.amazonaws.com",
            Parameter.region: "us-west-2",
            Parameter.endpoint_name: endpoint_name,
            Parameter.endpoint_config_name: "LEARNING-model-sim-public-1-0",
            Parameter.model_name: "model-sim-public",
            Parameter.instance_type: "ml.t2.medium",
            Parameter.initial_instance_count: "1",
            Parameter.steady_state_tps: "10",
        },
        requirements={},
    )
    manager = SageMakerEnvironmentManager()

    log.info("Check current state...")
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Tear down to known clean state...")
    manager.teardown(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Set up first config...")
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Set different traffic but should have no infra update...")
    config.parameters[Parameter.steady_state_tps] = "20"
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Set up new config...")
    config.parameters[Parameter.instance_type] = "ml.m5.large"
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Tear down...")
    manager.teardown(config)
    status = manager.get_status(endpoint_name)
    print(status)
