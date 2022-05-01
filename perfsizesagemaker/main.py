import argparse
from datetime import datetime
from decimal import Decimal
import json
import logging
import math
import os
import pathlib
from perfsize.perfsize import (
    lt,
    gte,
    Condition,
    Plan,
    Workflow,
)
from perfsize.reporter.mock import MockReporter
from perfsize.result.gatling import GatlingResultManager, Metric
from perfsizesagemaker.cost import CostEstimator
from perfsizesagemaker.environment.sagemaker import SageMakerEnvironmentManager
from perfsizesagemaker.load.sagemaker import SageMakerLoadManager
from perfsizesagemaker.reporter.html import HTMLReporter
from perfsizesagemaker.step.sagemaker import (
    FirstSuccessStepManager,
    AutoScaleMinFinderStepManager,
)
from perfsizesagemaker.constants import Parameter, SageMaker
from pprint import pformat
import sys
from typing import Dict, Optional
import yaml

log = logging.getLogger(__name__)


def get_timestamp_utc() -> str:
    """Return current time as a formatted string."""
    return datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")


def validate_scenario_requests(input: str) -> None:
    """Confirm request payload files are valid and weights sum to 100."""
    # TODO: See how to handle different file encoding types.
    items = json.loads(input)
    if not items:
        raise RuntimeError("ERROR: scenario must contain at least one element")
    sum_of_weights = 0
    for item in items:
        path = item["path"]
        if not pathlib.Path(path).exists():
            raise RuntimeError(f"ERROR: file {path} does not exist")
        weight = item["weight"]
        if weight < 0:
            raise RuntimeError(f"ERROR: file {path} had negative weight: {weight}")
        sum_of_weights = sum_of_weights + weight
    if sum_of_weights != 100:
        raise RuntimeError(f"ERROR: expected sum_of_weights=100, got: {sum_of_weights}")


class Main:
    def __init__(self) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument(
            "--iam_role_arn",
            help="role to assume to get credentials, otherwise will get credentials from environment",
            required=False,
        )
        parser.add_argument(
            "--host",
            help="SageMaker runtime host",
            required=True,
        )
        parser.add_argument(
            "--region",
            help="region name for boto3 and cost lookup",
            required=True,
        )
        parser.add_argument(
            "--endpoint_name", help="name of SageMaker Endpoint", required=True
        )
        parser.add_argument(
            "--endpoint_config_name",
            help="name of SageMaker EndpointConfig",
            required=True,
        )
        parser.add_argument(
            "--variant_name",
            help="name of SageMaker Endpoint Variant",
            default="variant-name-1",
        )
        parser.add_argument(
            "--model_name", help="name of SageMaker Model", required=True
        )
        parser.add_argument(
            "--scenario_requests",
            help="json array of request file paths and weights",
            required=True,
        )
        parser.add_argument("--peak_tps", help="required highest TPS", required=True)
        parser.add_argument(
            "--latency_success_p99", help="allowed p99 latency", required=True
        )
        parser.add_argument(
            "--percent_fail", help="allowed failure percentage", required=True
        )
        parser.add_argument(
            "--type_walk",
            help="comma separated instance types to test",
            required=True,
        )
        parser.add_argument(
            "--count_walk", help="comma separated counts to test", required=True
        )
        parser.add_argument(
            "--tps_walk", help="comma separated TPS values to test", required=True
        )
        parser.add_argument(
            "--duration_minutes", help="duration in minutes for type tests", default=3
        )
        parser.add_argument(
            "--endurance_ramp_start_tps",
            help="TPS at start of endurance test ramp",
            default=0,
        )
        parser.add_argument(
            "--endurance_ramp_minutes",
            help="duration in minutes for endurance test ramp",
            default=0,
        )
        parser.add_argument(
            "--endurance_steady_state_minutes",
            help="duration in minutes for endurance steady state",
            default=30,
        )
        parser.add_argument(
            "--endurance_retries",
            help="number of times to retry endurance test",
            default=3,
        )
        parser.add_argument(
            "--perfsize_results_dir",
            help="directory for saving test results",
            default="perfsize-results-dir",
        )
        parser.add_argument(
            "--cost_file",
            help="path to file mapping instance type to hourly rate",
            default="resources/configs/cost/us-west-2.json",
        )
        parser.add_argument(
            "--jar_file",
            help="path to sagmaker-gatling.jar file",
            default="sagemaker-gatling.jar",
        )
        parser.add_argument(
            "--logging_config",
            help="path to logging.yml file",
            default="resources/configs/logging/logging.yml",
        )
        args = parser.parse_args()

        # Tried setting type checking directly in add_argument but the error message
        # result was not specific enough and only showed a stacktrace on parse_args.
        # Do additional validation.
        self.iam_role_arn = args.iam_role_arn
        self.host = args.host
        self.region = args.region
        self.endpoint_name = args.endpoint_name
        self.endpoint_config_name = args.endpoint_config_name
        self.variant_name = args.variant_name
        self.model_name = args.model_name
        self.scenario_requests = args.scenario_requests
        try:
            json.loads(self.scenario_requests)
            validate_scenario_requests(self.scenario_requests)
        except:
            error = sys.exc_info()[0]
            description = sys.exc_info()[1]
            parser.error(
                f"argument --scenario_requests: got error {error}: {description}"
            )
        try:
            self.peak_tps = Decimal(args.peak_tps)
        except:
            parser.error(
                f"argument --peak_tps: expected a number but got: {args.peak_tps}"
            )
        try:
            self.latency_success_p99 = Decimal(args.latency_success_p99)
        except:
            parser.error(
                f"argument --latency_success_p99: expected a number but got: {args.latency_success_p99}"
            )
        try:
            self.percent_fail = Decimal(args.percent_fail)
        except:
            parser.error(
                f"argument --percent_fail: expected a number but got: {args.percent_fail}"
            )
        try:
            self.type_walk = args.type_walk.split(",")
        except:
            parser.error(
                f"argument --type_walk: expected a comma separated list of strings but got: {args.type_walk}"
            )
        try:
            self.count_walk = list(map(int, args.count_walk.split(",")))
        except:
            parser.error(
                f"argument --count_walk: expected a comma separated list of integers but got: {args.count_walk}"
            )
        try:
            self.tps_walk = list(map(Decimal, args.tps_walk.split(",")))
        except:
            parser.error(
                f"argument --tps_walk: expected a comma separated list of numbers but got: {args.tps_walk}"
            )
        try:
            self.duration_minutes = Decimal(args.duration_minutes)
        except:
            parser.error(
                f"argument --duration_minutes: expected a number but got: {args.duration_minutes}"
            )
        try:
            self.endurance_ramp_start_tps = Decimal(args.endurance_ramp_start_tps)
        except:
            parser.error(
                f"argument --endurance_ramp_start_tps: expected a number but got: {args.endurance_ramp_start_tps}"
            )
        try:
            self.endurance_ramp_minutes = Decimal(args.endurance_ramp_minutes)
        except:
            parser.error(
                f"argument --endurance_ramp_minutes: expected a number but got: {args.endurance_ramp_minutes}"
            )
        try:
            self.endurance_steady_state_minutes = Decimal(
                args.endurance_steady_state_minutes
            )
        except:
            parser.error(
                f"argument --endurance_steady_state_minutes: expected a number but got: {args.endurance_steady_state_minutes}"
            )
        try:
            self.endurance_retries = int(args.endurance_retries)
        except:
            parser.error(
                f"argument --endurance_retries: expected an integer but got: {args.endurance_retries}"
            )
        self.perfsize_results_dir = args.perfsize_results_dir
        if not os.path.isdir(self.perfsize_results_dir):
            os.mkdir(self.perfsize_results_dir)
        job_id = f"job-{get_timestamp_utc()}-{self.model_name}"
        self.job_id_dir = self.perfsize_results_dir + os.sep + job_id
        if not os.path.isdir(self.job_id_dir):
            os.mkdir(self.job_id_dir)
        try:
            self.cost_file = args.cost_file
            self.cost = CostEstimator(self.cost_file)
        except:
            parser.error(f"argument --cost_file: error loading {args.cost_file}")
        self.jar_file = args.jar_file
        if not pathlib.Path(self.jar_file).exists():
            parser.error(f"argument --jar_file not found: {self.jar_file}")
        self.logging_config = args.logging_config
        if not pathlib.Path(self.logging_config).exists():
            parser.error(f"argument --logging_config not found: {self.logging_config}")

        # Initialize logger if config file exists
        with open(self.logging_config, "r") as stream:
            config = yaml.safe_load(stream)
        logging.config.dictConfig(config)
        for name in logging.root.manager.loggerDict:  # type: ignore
            if name.startswith("perfsize"):
                logging.getLogger(name).setLevel(logging.DEBUG)

        # TODO: Make arg parsing more generic. For now, only handling latency_success_p99 and percent_fail.
        self.requirements = {
            Metric.latency_success_p99: [
                Condition(
                    lt(self.latency_success_p99),
                    f"latency_success_p99 < {self.latency_success_p99}",
                ),
                Condition(gte(Decimal("0")), "latency_success_p99 >= 0"),
            ],
            Metric.percent_fail: [
                Condition(lt(self.percent_fail), f"percent_fail < {self.percent_fail}"),
                Condition(gte(Decimal("0")), "percent_fail >= 0"),
            ],
        }
        log.info(f"Starting perfsize with requirements: {self.requirements}")

        # Track findings for each testing phase
        self.type_plan: Optional[Plan] = None
        self.max_count_plan: Optional[Plan] = None
        self.min_count_plan: Optional[Plan] = None
        self.recommend_type: Optional[Dict[str, str]] = None
        self.recommend_max: Optional[Dict[str, str]] = None
        self.recommend_min: Optional[Dict[str, str]] = None

    def test_type(self) -> Optional[Dict[str, str]]:
        # Phase 1: Find working instance type.
        # The goal is to find the first instance type that works and how much
        # load it can handle.
        # The count should default to 1, but user might override with a list of
        # higher counts. Final TPS per instance would just need to be calculated
        # accordingly.
        self.type_plan = Plan(
            parameter_lists={
                Parameter.host: [self.host],
                Parameter.region: [self.region],
                Parameter.endpoint_name: [self.endpoint_name],
                Parameter.endpoint_config_name: [self.endpoint_config_name],
                Parameter.variant_name: [self.variant_name],
                Parameter.model_name: [self.model_name],
                Parameter.instance_type: self.type_walk,
                Parameter.initial_instance_count: list(map(str, self.count_walk)),
                Parameter.ramp_start_tps: ["0"],
                Parameter.ramp_minutes: ["0"],
                Parameter.steady_state_tps: list(map(str, self.tps_walk)),
                Parameter.steady_state_minutes: [f"{self.duration_minutes}"],
            },
            requirements=self.requirements,
        )
        log.info(f"Testing instance type with plan: {self.type_plan}")

        type_workflow = Workflow(
            plan=self.type_plan,
            step_manager=FirstSuccessStepManager(self.type_plan),
            environment_manager=SageMakerEnvironmentManager(
                self.iam_role_arn, self.region
            ),
            load_manager=SageMakerLoadManager(
                scenario_requests=self.scenario_requests,
                gatling_jar_path=self.jar_file,
                gatling_scenario="GenericSageMakerScenario",
                gatling_results_path=self.job_id_dir,
                iam_role_arn=self.iam_role_arn,
                region=self.region,
            ),
            result_managers=[GatlingResultManager(results_path=self.job_id_dir)],
            reporters=[MockReporter()],
            teardown_between_steps=False,
            teardown_at_end=True,
        )
        type_recommendation = type_workflow.run()
        log.debug(
            f"Test for instance type got recommendation: {pformat(type_recommendation)}"
        )
        if not type_recommendation:
            log.error(f"Test failed to find a working instance type from given list.")
            return None

        instance_type = type_recommendation[Parameter.instance_type]
        initial_instance_count = Decimal(
            type_recommendation[Parameter.initial_instance_count]
        )
        steady_state_tps = Decimal(type_recommendation[Parameter.steady_state_tps])
        tps_per_instance = steady_state_tps / initial_instance_count
        instance_count_needed = math.ceil(self.peak_tps / tps_per_instance)
        recommend_type: Dict[str, str] = {}
        recommend_type[Parameter.instance_type] = instance_type
        recommend_type[Parameter.initial_instance_count] = f"{initial_instance_count}"
        recommend_type[Parameter.steady_state_tps] = f"{steady_state_tps}"
        recommend_type["tps_per_instance"] = f"{tps_per_instance}"
        recommend_type["instance_count_needed"] = f"{instance_count_needed}"
        recommend_type["explanation"] = (
            f"Last green run was {steady_state_tps} TPS supported by {initial_instance_count} instances of {instance_type}.\n"
            f"{steady_state_tps} / {initial_instance_count} = {tps_per_instance} TPS per instance.\n"
            f"To support {self.peak_tps} TPS, we need ceiling({self.peak_tps} / {tps_per_instance}) = {instance_count_needed} instances."
        )
        log.info(f"recommend_type: {pformat(recommend_type)}")
        return recommend_type

    def test_max(
        self, instance_type: str, instance_count_needed: int
    ) -> Optional[Dict[str, str]]:
        # Phase 2: Find instance count needed for max TPS.
        # Second set limits instance type to the one found above.
        # The goal is to find the number of instances needed to support given
        # peak load. This number is calculated as instance_count_needed,
        # assuming linear extrapolation. But just in case it fails,
        # the test plan includes some endurance_retries.

        self.max_count_plan = Plan(
            parameter_lists={
                Parameter.host: [self.host],
                Parameter.region: [self.region],
                Parameter.endpoint_name: [self.endpoint_name],
                Parameter.endpoint_config_name: [self.endpoint_config_name],
                Parameter.variant_name: [self.variant_name],
                Parameter.model_name: [self.model_name],
                Parameter.instance_type: [instance_type],
                Parameter.initial_instance_count: list(
                    map(
                        str,
                        range(
                            instance_count_needed,
                            instance_count_needed + self.endurance_retries + 1,
                        ),
                    )
                ),
                Parameter.ramp_start_tps: ["0"],
                Parameter.ramp_minutes: ["0"],
                Parameter.steady_state_tps: [f"{self.peak_tps}"],
                Parameter.steady_state_minutes: [
                    f"{self.endurance_steady_state_minutes}"
                ],
            },
            requirements=self.requirements,
        )
        log.info(f"Testing instance count with plan: {self.max_count_plan}")

        max_count_workflow = Workflow(
            plan=self.max_count_plan,
            step_manager=FirstSuccessStepManager(self.max_count_plan),
            environment_manager=SageMakerEnvironmentManager(
                self.iam_role_arn, self.region
            ),
            load_manager=SageMakerLoadManager(
                scenario_requests=self.scenario_requests,
                gatling_jar_path=self.jar_file,
                gatling_scenario="GenericSageMakerScenario",
                gatling_results_path=self.job_id_dir,
                iam_role_arn=self.iam_role_arn,
                region=self.region,
            ),
            result_managers=[GatlingResultManager(results_path=self.job_id_dir)],
            reporters=[MockReporter()],
            teardown_between_steps=True,
            teardown_at_end=True,
        )
        max_count_recommendation = max_count_workflow.run()
        log.debug(
            f"Test for instance count got recommendation: {pformat(max_count_recommendation)}"
        )
        if not max_count_recommendation:
            log.error(f"Test failed to find a working instance count for peak TPS.")
            return None

        max_instance_count = int(
            max_count_recommendation[Parameter.initial_instance_count]
        )
        max_steady_state_tps = Decimal(
            max_count_recommendation[Parameter.steady_state_tps]
        )
        max_tps_per_instance = max_steady_state_tps / max_instance_count
        invocations_target = int(
            self.peak_tps / max_instance_count * 60 * SageMaker.SAFETY_FACTOR
        )
        recommend_max: Dict[str, str] = {}
        recommend_max["max_instance_count"] = f"{max_instance_count}"
        recommend_max["max_steady_state_tps"] = f"{max_steady_state_tps}"
        recommend_max["max_tps_per_instance"] = f"{max_tps_per_instance}"
        recommend_max["max_cost"] = self.cost.explain(instance_type, max_instance_count)
        recommend_max["invocations_target"] = f"{invocations_target}"
        recommend_max["explanation"] = (
            f"Last green run was {max_steady_state_tps} TPS supported by {max_instance_count} instances of {instance_type}.\n"
            f"max_tps_per_instance = {max_steady_state_tps} / {max_instance_count} = {max_tps_per_instance} TPS per instance.\n"
            f"Autoscaling metric (SageMakerVariantInvocationsPerInstance):\n"
            f"= int(max_tps_per_instance * 60 seconds/minute * safety_factor)\n"
            f"= int({max_tps_per_instance} * 60 * {SageMaker.SAFETY_FACTOR})\n"
            f"= {invocations_target} invocations / instance / minute"
        )
        log.info(f"recommend_max: {pformat(recommend_max)}")
        return recommend_max

    def test_min(
        self, instance_type: str, max_instance_count: int, invocations_target: int
    ) -> Optional[Dict[str, str]]:
        # Phase 3: Find min instance count that can still support given ramp time.
        # Third set limits instance type and max count to values found above.
        # The goal is to find min number of instances needed to support given
        # ramp from starting TPS to peak TPS over ramp minutes.

        # Check if auto scale is even needed. TODO: make threshold configurable
        if max_instance_count == 1:
            log.info(f"No need for auto scale, 1 instance enough for peak TPS.")
            return None

        self.min_count_plan = Plan(
            parameter_lists={
                Parameter.host: [self.host],
                Parameter.region: [self.region],
                Parameter.endpoint_name: [self.endpoint_name],
                Parameter.endpoint_config_name: [self.endpoint_config_name],
                Parameter.variant_name: [self.variant_name],
                Parameter.model_name: [self.model_name],
                Parameter.instance_type: [instance_type],
                # omitting Parameter.initial_instance_count
                Parameter.scaling_enabled: ["True"],
                Parameter.scaling_min_instance_count: list(
                    map(
                        str,
                        range(1, max_instance_count + 1),
                    )
                ),
                Parameter.scaling_max_instance_count: [str(max_instance_count)],
                Parameter.scaling_metric: ["SageMakerVariantInvocationsPerInstance"],
                Parameter.scaling_target: [str(invocations_target)],
                Parameter.ramp_start_tps: [str(self.endurance_ramp_start_tps)],
                Parameter.ramp_minutes: [str(self.endurance_ramp_minutes)],
                Parameter.steady_state_tps: [str(self.peak_tps)],
                Parameter.steady_state_minutes: [
                    str(self.endurance_steady_state_minutes)
                ],
            },
            requirements=self.requirements,
        )
        log.info(f"Testing auto scale with plan: {self.min_count_plan}")

        min_count_workflow = Workflow(
            plan=self.min_count_plan,
            step_manager=AutoScaleMinFinderStepManager(self.min_count_plan),
            environment_manager=SageMakerEnvironmentManager(
                self.iam_role_arn, self.region
            ),
            load_manager=SageMakerLoadManager(
                scenario_requests=self.scenario_requests,
                gatling_jar_path=self.jar_file,
                gatling_scenario="GenericSageMakerScenario",
                gatling_results_path=self.job_id_dir,
                iam_role_arn=self.iam_role_arn,
                region=self.region,
            ),
            result_managers=[GatlingResultManager(results_path=self.job_id_dir)],
            reporters=[MockReporter()],
            teardown_between_steps=True,
            teardown_at_end=True,
        )
        min_count_recommendation = min_count_workflow.run()
        log.debug(
            f"Test for auto scale got recommendation: {pformat(min_count_recommendation)}"
        )
        if not min_count_recommendation:
            log.error(
                f"Test failed to find a working auto scale config for given requirements."
            )
            return None

        min_instance_count = int(
            min_count_recommendation[Parameter.scaling_min_instance_count]
        )
        scaling_metric = min_count_recommendation[Parameter.scaling_metric]
        scaling_target = min_count_recommendation[Parameter.scaling_target]
        ramp_start_tps = min_count_recommendation[Parameter.ramp_start_tps]
        ramp_minutes = min_count_recommendation[Parameter.ramp_minutes]
        steady_state_tps = min_count_recommendation[Parameter.steady_state_tps]
        steady_state_minutes = min_count_recommendation[Parameter.steady_state_minutes]
        recommend_min: Dict[str, str] = {}
        recommend_min["min_instance_count"] = str(min_instance_count)
        recommend_min["min_cost"] = self.cost.explain(instance_type, min_instance_count)
        recommend_min["explanation"] = (
            f"Traffic was {ramp_start_tps} TPS ramped over {ramp_minutes} minutes to {steady_state_tps} TPS, and then run for {steady_state_minutes} minutes.\n"
            f"Last green run was auto scale configuration with minimum {min_instance_count}, maximum {max_instance_count} instances of type {instance_type},\n"
            f"with scaling metric {scaling_metric} at {scaling_target} as calculated earlier.\n"
        )
        log.info(f"recommend_min: {pformat(recommend_min)}")
        return recommend_min

    def main(self) -> None:
        inputs: Dict[str, str] = {}
        inputs["iam_role_arn"] = f"{self.iam_role_arn}"
        inputs["host"] = f"{self.host}"
        inputs["region"] = f"{self.region}"
        inputs["endpoint_name"] = f"{self.endpoint_name}"
        inputs["endpoint_config_name"] = f"{self.endpoint_config_name}"
        inputs["variant_name"] = f"{self.variant_name}"
        inputs["model_name"] = f"{self.model_name}"
        inputs["scenario_requests"] = f"{self.scenario_requests}"
        inputs["peak_tps"] = f"{self.peak_tps}"
        inputs["latency_success_p99"] = f"{self.latency_success_p99}"
        inputs["percent_fail"] = f"{self.percent_fail}"
        inputs["type_walk"] = f"{self.type_walk}"
        inputs["count_walk"] = f"{self.count_walk}"
        inputs["tps_walk"] = f"{self.tps_walk}"
        inputs["duration_minutes"] = f"{self.duration_minutes}"
        inputs["endurance_ramp_start_tps"] = f"{self.endurance_ramp_start_tps}"
        inputs["endurance_ramp_minutes"] = f"{self.endurance_ramp_minutes}"
        inputs[
            "endurance_steady_state_minutes"
        ] = f"{self.endurance_steady_state_minutes}"
        inputs["endurance_retries"] = f"{self.endurance_retries}"
        inputs["perfsize_results_dir"] = f"{self.perfsize_results_dir}"
        inputs["job_id_dir"] = f"{self.job_id_dir}"
        inputs["cost_file"] = f"{self.cost_file}"
        inputs["jar_file"] = f"{self.jar_file}"
        inputs["logging_config"] = f"{self.logging_config}"
        log.debug(f"inputs: {pformat(inputs)}")

        self.recommend_type = self.test_type()

        if self.recommend_type:
            instance_type = self.recommend_type[Parameter.instance_type]
            instance_count_needed = int(self.recommend_type["instance_count_needed"])
            self.recommend_max = self.test_max(
                instance_type=instance_type, instance_count_needed=instance_count_needed
            )

            if self.recommend_max:
                max_instance_count = int(self.recommend_max["max_instance_count"])
                invocations_target = int(self.recommend_max["invocations_target"])
                self.recommend_min = self.test_min(
                    instance_type=instance_type,
                    max_instance_count=max_instance_count,
                    invocations_target=invocations_target,
                )

        # Generate final report...
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=self.type_plan,
            max_count_plan=self.max_count_plan,
            min_count_plan=self.min_count_plan,
            recommend_type=self.recommend_type,
            recommend_max=self.recommend_max,
            recommend_min=self.recommend_min,
        )
        content = reporter.render()
        report_file = f"{self.job_id_dir}/Final_Job_Report.html"
        with open(report_file, "w") as file:
            file.write(content)

        # TODO: Add flag to save files to S3...

        log.info(f"See report at {report_file}")


if __name__ == "__main__":
    m = Main()
    m.main()
