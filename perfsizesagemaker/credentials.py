import boto3
import logging.config
import os
from typing import Optional, Tuple

log = logging.getLogger(__name__)


class CredentialsManager:
    def __init__(
        self, iam_role_arn: Optional[str] = None, region: Optional[str] = None,
    ):
        self.iam_role_arn = iam_role_arn
        self.region = region

    def refresh(self) -> Tuple[str, str, str]:
        if self.iam_role_arn:
            client = boto3.client(service_name="sts", region_name=self.region)
            response = client.assume_role(
                RoleArn=self.iam_role_arn, RoleSessionName="test",
            )
            credentials = response["Credentials"]
            return (
                credentials["AccessKeyId"],
                credentials["SecretAccessKey"],
                credentials["SessionToken"],
            )
        else:
            return (
                os.environ["AWS_ACCESS_KEY_ID"],
                os.environ["AWS_SECRET_ACCESS_KEY"],
                os.environ["AWS_SESSION_TOKEN"],
            )
