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
# - Each Endpoint has at most one ScalableTarget and at most one ScalingPolicy.
# - ScalableTarget would define a DesiredInstanceCount with a min and max.
# - ScalingPolicy would be based on SageMakerVariantInvocationsPerInstance.
# - Only checking these fields for expected state when comparing and deciding
#   whether an update is needed. All other fields should be default.
class Endpoint:
    def __init__(
        self,
        endpoint_name: str,
        endpoint_status: str,
        endpoint_config_name: Optional[str] = None,
        variant_name: Optional[str] = None,
        current_instance_count: Optional[int] = None,
        desired_instance_count: Optional[int] = None,
    ):
        self.endpoint_name = endpoint_name
        self.endpoint_status = endpoint_status
        self.endpoint_config_name = endpoint_config_name
        self.variant_name = variant_name
        self.current_instance_count = current_instance_count
        self.desired_instance_count = desired_instance_count


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


class ScalableTarget:
    def __init__(
        self,
        scaling_min_instance_count: int,
        scaling_max_instance_count: int,
    ):
        self.scaling_min_instance_count = scaling_min_instance_count
        self.scaling_max_instance_count = scaling_max_instance_count


class ScalingPolicy:
    def __init__(
        self,
        scaling_metric: str,
        scaling_target: int,
    ):
        self.scaling_metric = scaling_metric
        self.scaling_target = scaling_target


class CombinedStatus:
    def __init__(
        self,
        endpoint_name: str,
        endpoint_status: str,
        endpoint_config_name: Optional[str] = None,
        variant_name: Optional[str] = None,
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
        self.variant_name = variant_name
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
            f"variant_name={self.variant_name}, "
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
            and self.variant_name == other.variant_name
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


# Sample response for describe_endpoint
#
# {
#   'EndpointName': 'LEARNING-model-simulator-1',
#   'EndpointArn': 'arn:aws:sagemaker:us-west-2:971083305877:endpoint/learning-model-simulator-1',
#   'EndpointConfigName': 'LEARNING-model-simulator-1-0',
#   'ProductionVariants': [
#     {
#       'VariantName': 'variant-name-1',
#       'DeployedImages': [
#         {
#           'SpecifiedImage': '971083305877.dkr.ecr.us-west-2.amazonaws.com/model-simulator:latest',
#           'ResolvedImage': '971083305877.dkr.ecr.us-west-2.amazonaws.com/model-simulator@sha256:c376bf3a856c840efe4589e1516898e35ad721835a2f78e294aab490cf115b0e',
#           'ResolutionTime': datetime.datetime(2021,11,19,15,11,46,682000,tzinfo=tzlocal())
#         }
#       ],
#       'CurrentWeight': 1.0,
#       'DesiredWeight': 1.0,
#       'CurrentInstanceCount': 1,
#       'DesiredInstanceCount': 1
#     }
#   ],
#   'EndpointStatus': 'InService',
#   'CreationTime': datetime.datetime(2021,11,19,15,11,45,370000,tzinfo=tzlocal()),
#   'LastModifiedTime': datetime.datetime(2021,11,19,15,13,50,265000,tzinfo=tzlocal()),
#   'ResponseMetadata': {
#     'RequestId': '393f1607-f6bd-4342-9a41-00db8824222b',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': '393f1607-f6bd-4342-9a41-00db8824222b',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '725',
#       'date': 'Sat, 20 Nov 2021 09:41:47 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }

# Sample response for describe_endpoint_config
#
# {
#   'EndpointConfigName': 'LEARNING-model-simulator-1-0',
#   'EndpointConfigArn': 'arn:aws:sagemaker:us-west-2:971083305877:endpoint-config/learning-model-simulator-1-0',
#   'ProductionVariants': [
#     {
#       'VariantName': 'variant-name-1',
#       'ModelName': 'model-simulator',
#       'InitialInstanceCount': 1,
#       'InstanceType': 'ml.t2.medium',
#       'InitialVariantWeight': 1.0
#     }
#   ],
#   'CreationTime': datetime.datetime(2021,11,19,15,11,44,822000,tzinfo=tzlocal()),
#   'ResponseMetadata': {
#     'RequestId': 'e2bc6e71-a00e-4809-aad0-cbff875fc576',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': 'e2bc6e71-a00e-4809-aad0-cbff875fc576',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '361',
#       'date': 'Sat, 20 Nov 2021 09:41:47 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }

# Sample response for describe_scalable_targets (empty example)
#
# {
#   'ScalableTargets': [],
#   'ResponseMetadata': {
#     'RequestId': 'b2786680-b870-4f82-8c56-b7418bbd13c4',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': 'b2786680-b870-4f82-8c56-b7418bbd13c4',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '22',
#       'date': 'Sat, 20 Nov 2021 23:04:02 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }

# Sample response for describe_scalable_targets (populated example)
#
# {
#   'ScalableTargets': [
#     {
#       'ServiceNamespace': 'sagemaker',
#       'ResourceId': 'endpoint/LEARNING-model-simulator-1/variant/variant-name-1',
#       'ScalableDimension': 'sagemaker:variant:DesiredInstanceCount',
#       'MinCapacity': 1,
#       'MaxCapacity': 2,
#       'RoleARN': 'arn:aws:iam::971083305877:role/aws-service-role/sagemaker.application-autoscaling.amazonaws.com/AWSServiceRoleForApplicationAutoScaling_SageMakerEndpoint',
#       'CreationTime': datetime.datetime(2021, 11, 20, 15, 40, 47, 572000, tzinfo=tzlocal()),
#       'SuspendedState': {
#         'DynamicScalingInSuspended': False,
#         'DynamicScalingOutSuspended': False,
#         'ScheduledScalingSuspended': False
#       }
#     }
#   ],
#   'ResponseMetadata': {
#     'RequestId': 'd1a6e66c-be90-426d-bfe9-eea6b079f7c1',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': 'd1a6e66c-be90-426d-bfe9-eea6b079f7c1',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '541',
#       'date': 'Sat, 20 Nov 2021 23:44:24 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }

# Sample response for describe_scaling_policies (empty example)
#
# {
#   'ScalingPolicies': [],
#   'ResponseMetadata': {
#     'RequestId': '0242dba0-4f0f-401b-8301-4ac8e87b4fcc',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': '0242dba0-4f0f-401b-8301-4ac8e87b4fcc',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '22',
#       'date': 'Sat, 20 Nov 2021 11:50:38 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }

# Sample response for describe_scaling_policies (populated example)
#
# {
#   'ScalingPolicies': [
#     {
#       'PolicyARN': 'arn:aws:autoscaling:us-west-2:971083305877:scalingPolicy:5e076780-e945-4cdf-8b1d-18a8d675fd71:resource/sagemaker/endpoint/LEARNING-model-simulator-1/variant/variant-name-1:policyName/SageMakerEndpointInvocationScalingPolicy',
#       'PolicyName': 'SageMakerEndpointInvocationScalingPolicy',
#       'ServiceNamespace': 'sagemaker',
#       'ResourceId': 'endpoint/LEARNING-model-simulator-1/variant/variant-name-1',
#       'ScalableDimension': 'sagemaker:variant:DesiredInstanceCount',
#       'PolicyType': 'TargetTrackingScaling',
#       'TargetTrackingScalingPolicyConfiguration': {
#         'TargetValue': 100.0,
#         'PredefinedMetricSpecification': {
#           'PredefinedMetricType': 'SageMakerVariantInvocationsPerInstance'
#         },
#         'ScaleOutCooldown': 300,
#         'ScaleInCooldown': 300,
#         'DisableScaleIn': False
#       },
#       'Alarms': [
#         {
#           'AlarmName': 'TargetTracking-endpoint/LEARNING-model-simulator-1/variant/variant-name-1-AlarmHigh-609224a3-ce77-4cf9-98c7-0d5211b1fec2',
#           'AlarmARN': 'arn:aws:cloudwatch:us-west-2:971083305877:alarm:TargetTracking-endpoint/LEARNING-model-simulator-1/variant/variant-name-1-AlarmHigh-609224a3-ce77-4cf9-98c7-0d5211b1fec2'
#         },
#         {
#           'AlarmName': 'TargetTracking-endpoint/LEARNING-model-simulator-1/variant/variant-name-1-AlarmLow-6148a0e4-e90a-403d-9130-b6a4b3265926',
#           'AlarmARN': 'arn:aws:cloudwatch:us-west-2:971083305877:alarm:TargetTracking-endpoint/LEARNING-model-simulator-1/variant/variant-name-1-AlarmLow-6148a0e4-e90a-403d-9130-b6a4b3265926'
#         }
#       ],
#       'CreationTime': datetime.datetime(2021, 11, 20, 15, 40, 48, 691000, tzinfo=tzlocal())
#     }
#   ],
#   'ResponseMetadata': {
#     'RequestId': '1fe50dcf-b2be-4bec-a005-bc2ef27ed5ef',
#     'HTTPStatusCode': 200,
#     'HTTPHeaders': {
#       'x-amzn-requestid': '1fe50dcf-b2be-4bec-a005-bc2ef27ed5ef',
#       'content-type': 'application/x-amz-json-1.1',
#       'content-length': '1430',
#       'date': 'Sat, 20 Nov 2021 23:44:24 GMT'
#     },
#     'RetryAttempts': 0
#   }
# }


class SageMakerEnvironmentManager(EnvironmentManager):
    def __init__(
        self,
        iam_role_arn: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.credentials_manager = CredentialsManager(iam_role_arn, region)
        self.region = region

    def _client(self, service_name: str) -> boto3.session.Session.client:
        (
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        ) = self.credentials_manager.refresh()
        return boto3.client(
            service_name=service_name,
            region_name=self.region,
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
        )

    def _sagemaker_client(self) -> boto3.session.Session.client:
        return self._client("sagemaker")

    def _autoscaling_client(self) -> boto3.session.Session.client:
        return self._client("application-autoscaling")

    def get_endpoint_config(
        self, endpoint_config_name: str
    ) -> Optional[EndpointConfig]:
        sagemaker = self._sagemaker_client()
        try:
            response = sagemaker.describe_endpoint_config(
                EndpointConfigName=endpoint_config_name
            )
        except ClientError as err:
            if err.args and "Could not find endpoint configuration" in err.args[0]:
                log.debug(f"EndpointConfig {endpoint_config_name} not found.")
                return None
            else:
                raise err
        log.debug(f"EndpointConfig {endpoint_config_name} description: {response}")
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

    def get_endpoint(self, endpoint_name: str) -> Endpoint:
        sagemaker = self._sagemaker_client()
        try:
            response = sagemaker.describe_endpoint(EndpointName=endpoint_name)
        except ClientError as err:
            if err.args and "Could not find endpoint" in err.args[0]:
                return Endpoint(
                    endpoint_name=endpoint_name,
                    endpoint_status="NotFound",
                )
            else:
                raise (err)
        log.debug(f"Endpoint {endpoint_name} description: {response}")
        assert response["EndpointName"] == endpoint_name
        endpoint_config_name = None
        variant_name = None
        current_instance_count = None
        desired_instance_count = None
        if "EndpointConfigName" in response:
            endpoint_config_name = response["EndpointConfigName"]
        if "ProductionVariants" in response:
            # Some states like "Creating" do not have ProductionVariants yet
            assert len(response["ProductionVariants"]) == 1
            variant = response["ProductionVariants"][0]
            variant_name = variant["VariantName"]
            current_instance_count = variant["CurrentInstanceCount"]
            desired_instance_count = variant["DesiredInstanceCount"]
        endpoint_status = response["EndpointStatus"]
        return Endpoint(
            endpoint_name=endpoint_name,
            endpoint_status=endpoint_status,
            endpoint_config_name=endpoint_config_name,
            variant_name=variant_name,
            current_instance_count=current_instance_count,
            desired_instance_count=desired_instance_count,
        )

    def get_scalable_target(self, resource_id: str) -> Optional[ScalableTarget]:
        autoscaling = self._autoscaling_client()
        response = autoscaling.describe_scalable_targets(
            ServiceNamespace="sagemaker", ResourceIds=[resource_id]
        )
        log.debug(f"ScalableTargets for {resource_id} description: {response}")
        if response["ScalableTargets"]:
            assert len(response["ScalableTargets"]) == 1
            target = response["ScalableTargets"][0]
            assert target["ResourceId"] == resource_id
            return ScalableTarget(
                scaling_min_instance_count=target["MinCapacity"],
                scaling_max_instance_count=target["MaxCapacity"],
            )
        return None

    def get_scaling_policy(self, resource_id: str) -> Optional[ScalingPolicy]:
        autoscaling = self._autoscaling_client()
        response = autoscaling.describe_scaling_policies(
            ServiceNamespace="sagemaker", ResourceId=resource_id
        )
        log.debug(f"ScalingPolicies for {resource_id} description: {response}")
        if response["ScalingPolicies"]:
            assert len(response["ScalingPolicies"]) == 1
            policy = response["ScalingPolicies"][0]
            assert policy["ResourceId"] == resource_id
            return ScalingPolicy(
                scaling_metric=policy["TargetTrackingScalingPolicyConfiguration"][
                    "PredefinedMetricSpecification"
                ]["PredefinedMetricType"],
                scaling_target=policy["TargetTrackingScalingPolicyConfiguration"][
                    "TargetValue"
                ],
            )
        return None

    def _resource_id(self, endpoint_name: str, variant_name: str) -> str:
        return f"endpoint/{endpoint_name}/variant/{variant_name}"

    def get_status(self, endpoint_name: str) -> CombinedStatus:
        # Check Endpoint
        endpoint = self.get_endpoint(endpoint_name)
        if endpoint.endpoint_status == "NotFound":
            return CombinedStatus(
                endpoint_name=endpoint_name,
                endpoint_status="NotFound",
            )
        endpoint_config_name = endpoint.endpoint_config_name
        if not endpoint_config_name:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} has endpoint_config_name={endpoint_config_name}"
            )
        if not endpoint.variant_name:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} has variant_name={endpoint.variant_name}"
            )
        resource_id = self._resource_id(endpoint_name, endpoint.variant_name)

        # Check EndpointConfig
        endpoint_config = self.get_endpoint_config(endpoint_config_name)
        if endpoint_config is None:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} is pointing to EndpointConfig {endpoint_config_name}, but the config cannot be found."
            )

        # Check auto scale settings. Default is off.
        scaling_enabled = False
        scaling_min_instance_count = None
        scaling_max_instance_count = None
        scaling_metric = None
        scaling_target = None

        # Check ScalableTargets
        target = self.get_scalable_target(resource_id)
        if target:
            scaling_enabled = True
            scaling_min_instance_count = target.scaling_min_instance_count
            scaling_max_instance_count = target.scaling_max_instance_count

        # Check ScalingPolicies
        policy = self.get_scaling_policy(resource_id)
        if policy:
            scaling_enabled = True
            scaling_metric = policy.scaling_metric
            scaling_target = policy.scaling_target

        return CombinedStatus(
            endpoint_name=endpoint_name,
            endpoint_status=endpoint.endpoint_status,
            endpoint_config_name=endpoint_config_name,
            variant_name=endpoint.variant_name,
            model_name=endpoint_config.model_name,
            instance_type=endpoint_config.instance_type,
            initial_instance_count=endpoint_config.initial_instance_count,
            current_instance_count=endpoint.current_instance_count,
            desired_instance_count=endpoint.desired_instance_count,
            scaling_enabled=scaling_enabled,
            scaling_min_instance_count=scaling_min_instance_count,
            scaling_max_instance_count=scaling_max_instance_count,
            scaling_metric=scaling_metric,
            scaling_target=scaling_target,
        )

    def delete_auto_scaling(self, endpoint_name: str) -> None:
        log.debug(
            f"About to delete auto scaling settings for Endpoint {endpoint_name}..."
        )
        autoscaling = self._autoscaling_client()

        # Check Endpoint
        endpoint = self.get_endpoint(endpoint_name)
        if endpoint.endpoint_status == "NotFound":
            log.debug(f"Endpoint {endpoint_name} not found, so nothing to remove")
            return
        if not endpoint.variant_name:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} has variant_name={endpoint.variant_name}"
            )
        resource_id = self._resource_id(endpoint_name, endpoint.variant_name)

        # Check ScalableTargets
        target = self.get_scalable_target(resource_id)
        if target:
            response = autoscaling.deregister_scalable_target(
                ServiceNamespace="sagemaker",
                ResourceId=resource_id,
                ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            )
            log.debug(f"Removed scalable target for resource {resource_id}: {response}")
        else:
            log.debug(f"No scalable target found for resource {resource_id}")

        # Check ScalingPolicies
        policy = self.get_scaling_policy(resource_id)
        if policy:
            response = autoscaling.delete_scaling_policy(
                PolicyName="SageMakerEndpointInvocationScalingPolicy",
                ServiceNamespace="sagemaker",
                ResourceId=resource_id,
                ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            )
            log.debug(f"Removed scaling policy for resource {resource_id}: {response}")
        else:
            log.debug(f"No scaling policy found for resource {resource_id}")

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
        variant_name: str,
        model_name: str,
        initial_instance_count: int,
        instance_type: str,
    ) -> None:
        client = self._sagemaker_client()
        response = client.create_endpoint_config(
            EndpointConfigName=endpoint_config_name,
            ProductionVariants=[
                {
                    "VariantName": variant_name,
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
                f"ERROR: Endpoint {endpoint_name} cannot be created if EndpointConfig {endpoint_config_name} is not found."
            )

        client = self._sagemaker_client()
        response = client.create_endpoint(
            EndpointName=endpoint_name,
            EndpointConfigName=endpoint_config_name,
        )
        log.debug(f"Endpoint {endpoint_name} creation response {response}")
        self.wait_endpoint_in_service(endpoint_name)

    def create_auto_scaling(
        self,
        endpoint_name: str,
        scaling_min_instance_count: int,
        scaling_max_instance_count: int,
        scaling_target: int,
    ) -> None:
        log.debug(
            f"About to create auto scaling settings for Endpoint {endpoint_name}..."
        )
        autoscaling = self._autoscaling_client()

        # Check Endpoint
        endpoint = self.get_endpoint(endpoint_name)
        if endpoint.endpoint_status == "NotFound":
            raise RuntimeError(
                f"ERROR: Could not create auto scaling because Endpoint {endpoint_name} not found."
            )
        if not endpoint.variant_name:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} has variant_name={endpoint.variant_name}"
            )
        resource_id = self._resource_id(endpoint_name, endpoint.variant_name)

        # Check ScalableTargets
        target = self.get_scalable_target(resource_id)
        if target:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} already has scalable target."
            )
        response = autoscaling.register_scalable_target(
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            MinCapacity=scaling_min_instance_count,
            MaxCapacity=scaling_max_instance_count,
        )
        log.debug(f"Created scalable target for resource {resource_id}: {response}")

        # Check ScalingPolicies
        policy = self.get_scaling_policy(resource_id)
        if policy:
            raise RuntimeError(
                f"ERROR: Endpoint {endpoint_name} already has scaling policy."
            )
        response = autoscaling.put_scaling_policy(
            PolicyName="SageMakerEndpointInvocationScalingPolicy",
            ServiceNamespace="sagemaker",
            ResourceId=resource_id,
            PolicyType="TargetTrackingScaling",
            ScalableDimension="sagemaker:variant:DesiredInstanceCount",
            TargetTrackingScalingPolicyConfiguration={
                "TargetValue": scaling_target,
                "PredefinedMetricSpecification": {
                    "PredefinedMetricType": "SageMakerVariantInvocationsPerInstance",
                },
            },
        )
        log.debug(f"Created scaling policy for resource {resource_id}: {response}")

    def teardown(self, config: Config) -> None:
        endpoint_name = config.parameters[Parameter.endpoint_name]
        endpoint_config_name = config.parameters[Parameter.endpoint_config_name]

        self.delete_auto_scaling(endpoint_name)

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
        variant_name = config.parameters[Parameter.variant_name]
        model_name = config.parameters[Parameter.model_name]
        instance_type = config.parameters[Parameter.instance_type]

        scaling_enabled = False
        scaling_min_instance_count = None
        scaling_max_instance_count = None
        scaling_metric = None
        scaling_target = None
        if (
            Parameter.scaling_enabled in config.parameters
            and config.parameters[Parameter.scaling_enabled] == "True"
        ):
            scaling_enabled = True
            scaling_min_instance_count = int(
                config.parameters[Parameter.scaling_min_instance_count]
            )
            scaling_max_instance_count = int(
                config.parameters[Parameter.scaling_max_instance_count]
            )
            scaling_metric = config.parameters[Parameter.scaling_metric]
            scaling_target = int(config.parameters[Parameter.scaling_target])

        # To help reduce combinations, initial_instance_count may be omitted if
        # scaling_enabled and will default to match scaling_min_instance_count.
        # But can still specify initial count explicitly if needed.
        if (
            scaling_enabled
            and Parameter.initial_instance_count not in config.parameters
        ):
            assert isinstance(scaling_min_instance_count, int)  # help mypy
            initial_instance_count = scaling_min_instance_count
        else:
            initial_instance_count = int(
                config.parameters[Parameter.initial_instance_count]
            )

        # Check if current state already set correctly
        expected = CombinedStatus(
            endpoint_name=endpoint_name,
            endpoint_status="InService",
            endpoint_config_name=endpoint_config_name,
            variant_name=variant_name,
            model_name=model_name,
            instance_type=instance_type,
            initial_instance_count=initial_instance_count,
            current_instance_count=initial_instance_count,
            desired_instance_count=initial_instance_count,
            scaling_enabled=scaling_enabled,
            scaling_min_instance_count=scaling_min_instance_count,
            scaling_max_instance_count=scaling_max_instance_count,
            scaling_metric=scaling_metric,
            scaling_target=scaling_target,
        )
        actual = self.get_status(endpoint_name)
        if actual == expected:
            log.info(f"No environment update needed: {actual}")
            return

        self.teardown(config)
        self.create_endpoint_config(
            endpoint_config_name=endpoint_config_name,
            variant_name=variant_name,
            model_name=model_name,
            initial_instance_count=initial_instance_count,
            instance_type=instance_type,
        )
        self.create_endpoint(
            endpoint_name=endpoint_name, endpoint_config_name=endpoint_config_name
        )
        if scaling_enabled:
            if not scaling_min_instance_count:
                raise RuntimeError(
                    f"ERROR: scaling_enabled so scaling_min_instance_count={scaling_min_instance_count} must be greater than 0."
                )
            if not scaling_max_instance_count:
                raise RuntimeError(
                    f"ERROR: scaling_enabled so scaling_max_instance_count={scaling_max_instance_count} must be greater than 0."
                )
            if not scaling_target:
                raise RuntimeError(
                    f"ERROR: scaling_enabled so scaling_target={scaling_target} must be greater than 0."
                )
            self.create_auto_scaling(
                endpoint_name=endpoint_name,
                scaling_min_instance_count=scaling_min_instance_count,
                scaling_max_instance_count=scaling_max_instance_count,
                scaling_target=scaling_target,
            )
        actual = self.get_status(endpoint_name)
        if actual != expected:
            raise RuntimeError(
                f"ERROR: setup failed to create state "
                f"\nexpected: {expected}"
                f"\nactual: {actual}"
            )

    # TODO: Add option to do a configurable warmup run when endpoint changes


if __name__ == "__main__":
    with open("resources/configs/logging/logging.yml", "r") as stream:
        log_config = yaml.safe_load(stream)
    logging.config.dictConfig(log_config)
    for name in logging.root.manager.loggerDict:  # type: ignore
        if name.startswith("perfsize"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    # TODO: move below to tests

    endpoint_name = "LEARNING-model-simulator-1"
    config = Config(
        parameters={
            Parameter.host: "runtime.sagemaker.us-west-2.amazonaws.com",
            Parameter.region: "us-west-2",
            Parameter.endpoint_name: endpoint_name,
            Parameter.endpoint_config_name: "LEARNING-model-simulator-1-0",
            Parameter.variant_name: "variant-name-1",
            Parameter.model_name: "model-simulator",
            Parameter.instance_type: "ml.t2.medium",
            Parameter.initial_instance_count: "1",
            Parameter.scaling_enabled: "False",
            Parameter.scaling_min_instance_count: "0",
            Parameter.scaling_max_instance_count: "0",
            Parameter.scaling_metric: "SageMakerVariantInvocationsPerInstance",
            Parameter.scaling_target: "0",
            Parameter.ramp_start_tps: "0",
            Parameter.ramp_minutes: "0",
            Parameter.steady_state_tps: "10",
            Parameter.steady_state_minutes: "3",
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

    log.info("Set up new config with different instance type...")
    config.parameters[Parameter.instance_type] = "ml.m5.large"
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Set up new config with auto scaling...")
    config.parameters[Parameter.scaling_enabled] = "True"
    config.parameters[Parameter.scaling_min_instance_count] = "1"
    config.parameters[Parameter.scaling_max_instance_count] = "2"
    config.parameters[
        Parameter.scaling_metric
    ] = "SageMakerVariantInvocationsPerInstance"
    config.parameters[Parameter.scaling_target] = "100"
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Set up new config auto scaling, no explicit initial count...")
    del config.parameters[Parameter.initial_instance_count]
    config.parameters[Parameter.scaling_min_instance_count] = "2"
    config.parameters[Parameter.scaling_max_instance_count] = "4"
    manager.setup(config)
    status = manager.get_status(endpoint_name)
    print(status)

    log.info("Tear down...")
    manager.teardown(config)
    status = manager.get_status(endpoint_name)
    print(status)
