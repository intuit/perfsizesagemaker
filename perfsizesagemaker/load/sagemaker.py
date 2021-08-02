from datetime import datetime
from decimal import Decimal
import logging.config
from perfsize.perfsize import Config, LoadManager, Run
from perfsizesagemaker.environment.sagemaker import SageMakerEnvironmentManager
from perfsizesagemaker.constants import Parameter
from perfsizesagemaker.credentials import CredentialsManager
import subprocess
from typing import Optional
import yaml

log = logging.getLogger(__name__)


class SageMakerLoadManager(LoadManager):
    def __init__(
        self,
        scenario_requests: str,
        gatling_jar_path: str,
        gatling_scenario: str,
        gatling_results_path: str,
        iam_role_arn: Optional[str] = None,
        region: Optional[str] = None,
    ):
        self.scenario_requests = scenario_requests
        self.gatling_jar_path = gatling_jar_path
        self.gatling_scenario = gatling_scenario
        self.gatling_results_path = gatling_results_path
        self.credentials_manager = CredentialsManager(iam_role_arn, region)

    def send(self, config: Config) -> Run:
        log.debug(f"SageMakerLoadManager will send load per config {config}")
        host = config.parameters[Parameter.host]
        region = config.parameters[Parameter.region]
        sagemaker_endpoint = config.parameters[Parameter.endpoint_name]
        scenario_ramp_start_tps = Decimal(config.parameters[Parameter.ramp_start_tps])
        scenario_ramp_minutes = Decimal(config.parameters[Parameter.ramp_minutes])
        scenario_steady_state_tps = Decimal(
            config.parameters[Parameter.steady_state_tps]
        )
        scenario_steady_state_minutes = Decimal(
            config.parameters[Parameter.steady_state_minutes]
        )
        start = datetime.utcnow()
        gatling_run_tag = (
            f"{int(start.timestamp())}-"
            f"{config.parameters[Parameter.instance_type]}-"
            f"{config.parameters[Parameter.initial_instance_count]}-"
            f"{scenario_steady_state_tps}TPS"
        )
        (
            aws_access_key_id,
            aws_secret_access_key,
            aws_session_token,
        ) = self.credentials_manager.refresh()
        completed = subprocess.run(
            [
                f"java",
                f"-Dgatling.core.outputDirectoryBaseName={gatling_run_tag}",
                f"-Dauth.awsAccessKeyId={aws_access_key_id}",
                f"-Dauth.awsSecretAccessKey={aws_secret_access_key}",
                f"-Dauth.awsSessionToken={aws_session_token}",
                f"-Dsagemaker.host={host}",
                f"-Dsagemaker.region={region}",
                f"-Dsagemaker.endpoint={sagemaker_endpoint}",
                f"-Dscenario.rampStartTps={scenario_ramp_start_tps}",
                f"-Dscenario.rampMinutes={scenario_ramp_minutes}",
                f"-Dscenario.steadyStateTps={scenario_steady_state_tps}",
                f"-Dscenario.steadyStateMinutes={scenario_steady_state_minutes}",
                f"-Dscenario.requests={self.scenario_requests}",
                f"-jar",
                f"{self.gatling_jar_path}",
                f"-s",
                f"{self.gatling_scenario}",
                f"-rf",
                f"{self.gatling_results_path}",
            ]
        )
        completed.check_returncode()
        end = datetime.utcnow()
        return Run(id=gatling_run_tag, start=start, end=end, results=[])


if __name__ == "__main__":
    with open("logging.yml", "r") as stream:
        log_config = yaml.safe_load(stream)
    logging.config.dictConfig(log_config)
    for name in logging.root.manager.loggerDict:  # type: ignore
        if name.startswith("perfsize"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    log.debug("yo")

    # plan

    # step_manager = StepManager(sample_plan)

    config = Config(
        parameters={
            Parameter.host: "runtime.sagemaker.us-west-2.amazonaws.com",
            Parameter.region: "us-west-2",
            Parameter.endpoint_name: "LEARNING-model-sim-public-1",
            Parameter.endpoint_config_name: "LEARNING-model-sim-public-1-0",
            Parameter.model_name: "model-sim-public",
            Parameter.instance_type: "ml.t2.medium",
            Parameter.initial_instance_count: "1",
            Parameter.ramp_start_tps: "0",
            Parameter.ramp_minutes: "0",
            Parameter.steady_state_tps: "1",
            Parameter.steady_state_minutes: "1",
        },
        requirements={},
    )
    environment_manager = SageMakerEnvironmentManager()
    environment_manager.setup(config)

    load_manager = SageMakerLoadManager(
        scenario_requests="""
            [
                {
                  "path": "bodies/model-sim/1/status-200.input.json",
                  "weight": 100
                }
            ]
        """,
        gatling_jar_path="./sagemaker-gatling.jar",
        gatling_scenario="GenericSageMakerScenario",
        gatling_results_path="./perfsize-results-root",
    )
    run = load_manager.send(config)

    # environment_manager.teardown(config)

    # result_manager = ResultManager()
    # result_manager.query(config, run)
