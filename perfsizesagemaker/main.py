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
    lte,
    gt,
    gte,
    eq,
    neq,
    Condition,
    Result,
    Run,
    Config,
    Plan,
    StepManager,
    EnvironmentManager,
    LoadManager,
    ResultManager,
    Reporter,
    Workflow,
)
from perfsize.reporter.mock import MockReporter
from perfsize.result.gatling import GatlingResultManager, Metric
from perfsizesagemaker.cost import CostEstimator
from perfsizesagemaker.environment.sagemaker import SageMakerEnvironmentManager
from perfsizesagemaker.load.sagemaker import SageMakerLoadManager
from perfsizesagemaker.reporter.html import HTMLReporter
from perfsizesagemaker.step.sagemaker import FirstSuccessStepManager
from perfsizesagemaker.constants import Parameter, SageMaker
from pprint import pformat, pprint
import sys
from typing import Dict, List
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
    sum = 0
    for item in items:
        path = item["path"]
        if not pathlib.Path(path).exists():
            raise RuntimeError(f"ERROR: file {path} does not exist")
        weight = item["weight"]
        if weight < 0:
            raise RuntimeError(f"ERROR: file {path} had negative weight: {weight}")
        sum = sum + weight
    if sum != 100:
        raise RuntimeError(f"ERROR: expected sum=100, got: {sum}")


def main() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--iam_role_arn",
        help="role to assume to get credentials, otherwise will get credentials from environment",
        required=False,
    )
    parser.add_argument(
        "--host", help="SageMaker runtime host", required=True,
    )
    parser.add_argument(
        "--region", help="region name for boto3 and cost lookup", required=True,
    )
    parser.add_argument(
        "--endpoint_name", help="name of SageMaker Endpoint", required=True
    )
    parser.add_argument(
        "--endpoint_config_name",
        help="name of SageMaker EndpointConfig",
        required=True,
    )
    parser.add_argument("--model_name", help="name of SageMaker Model", required=True)
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
        "--type_walk", help="comma separated instance types to test", required=True,
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
    iam_role_arn = args.iam_role_arn
    host = args.host
    region = args.region
    endpoint_name = args.endpoint_name
    endpoint_config_name = args.endpoint_config_name
    model_name = args.model_name
    scenario_requests = args.scenario_requests
    try:
        json.loads(scenario_requests)
        validate_scenario_requests(scenario_requests)
    except:
        error = sys.exc_info()[0]
        description = sys.exc_info()[1]
        parser.error(f"argument --scenario_requests: got error {error}: {description}")
    try:
        peak_tps = Decimal(args.peak_tps)
    except:
        parser.error(f"argument --peak_tps: expected a number but got: {args.peak_tps}")
    try:
        latency_success_p99 = Decimal(args.latency_success_p99)
    except:
        parser.error(
            f"argument --latency_success_p99: expected a number but got: {args.latency_success_p99}"
        )
    try:
        percent_fail = Decimal(args.percent_fail)
    except:
        parser.error(
            f"argument --percent_fail: expected a number but got: {args.percent_fail}"
        )
    try:
        type_walk = args.type_walk.split(",")
    except:
        parser.error(
            f"argument --type_walk: expected a comma separated list of strings but got: {args.type_walk}"
        )
    try:
        count_walk = list(map(int, args.count_walk.split(",")))
    except:
        parser.error(
            f"argument --count_walk: expected a comma separated list of integers but got: {args.count_walk}"
        )
    try:
        tps_walk = list(map(Decimal, args.tps_walk.split(",")))
    except:
        parser.error(
            f"argument --tps_walk: expected a comma separated list of numbers but got: {args.tps_walk}"
        )
    try:
        duration_minutes = Decimal(args.duration_minutes)
    except:
        parser.error(
            f"argument --duration_minutes: expected a number but got: {args.duration_minutes}"
        )
    try:
        endurance_ramp_start_tps = Decimal(args.endurance_ramp_start_tps)
    except:
        parser.error(
            f"argument --endurance_ramp_start_tps: expected a number but got: {args.endurance_ramp_start_tps}"
        )
    try:
        endurance_ramp_minutes = Decimal(args.endurance_ramp_minutes)
    except:
        parser.error(
            f"argument --endurance_ramp_minutes: expected a number but got: {args.endurance_ramp_minutes}"
        )
    try:
        endurance_steady_state_minutes = Decimal(args.endurance_steady_state_minutes)
    except:
        parser.error(
            f"argument --endurance_steady_state_minutes: expected a number but got: {args.endurance_steady_state_minutes}"
        )
    try:
        endurance_retries = int(args.endurance_retries)
    except:
        parser.error(
            f"argument --endurance_retries: expected an integer but got: {args.endurance_retries}"
        )
    perfsize_results_dir = args.perfsize_results_dir
    if not os.path.isdir(perfsize_results_dir):
        os.mkdir(perfsize_results_dir)
    job_id = f"job-{get_timestamp_utc()}-{model_name}"
    job_id_dir = perfsize_results_dir + os.sep + job_id
    if not os.path.isdir(job_id_dir):
        os.mkdir(job_id_dir)
    try:
        cost_file = args.cost_file
        cost = CostEstimator(cost_file)
    except:
        parser.error(f"argument --cost_file: error loading {args.cost_file}")
    jar_file = args.jar_file
    if not pathlib.Path(jar_file).exists():
        parser.error(f"argument --jar_file not found: {jar_file}")
    logging_config = args.logging_config
    if not pathlib.Path(logging_config).exists():
        parser.error(f"argument --logging_config not found: {logging_config}")

    # Initialize logger if config file exists
    with open(logging_config, "r") as stream:
        config = yaml.safe_load(stream)
    logging.config.dictConfig(config)
    for name in logging.root.manager.loggerDict:  # type: ignore
        if name.startswith("perfsize"):
            logging.getLogger(name).setLevel(logging.DEBUG)

    inputs: Dict[str, str] = {}
    inputs["iam_role_arn"] = f"{iam_role_arn}"
    inputs["host"] = f"{host}"
    inputs["region"] = f"{region}"
    inputs["endpoint_name"] = f"{endpoint_name}"
    inputs["endpoint_config_name"] = f"{endpoint_config_name}"
    inputs["model_name"] = f"{model_name}"
    inputs["scenario_requests"] = f"{scenario_requests}"
    inputs["peak_tps"] = f"{peak_tps}"
    inputs["latency_success_p99"] = f"{latency_success_p99}"
    inputs["percent_fail"] = f"{percent_fail}"
    inputs["type_walk"] = f"{type_walk}"
    inputs["count_walk"] = f"{count_walk}"
    inputs["tps_walk"] = f"{tps_walk}"
    inputs["duration_minutes"] = f"{duration_minutes}"
    inputs["endurance_ramp_start_tps"] = f"{endurance_ramp_start_tps}"
    inputs["endurance_ramp_minutes"] = f"{endurance_ramp_minutes}"
    inputs["endurance_steady_state_minutes"] = f"{endurance_steady_state_minutes}"
    inputs["endurance_retries"] = f"{endurance_retries}"
    inputs["perfsize_results_dir"] = f"{perfsize_results_dir}"
    inputs["job_id_dir"] = f"{job_id_dir}"
    inputs["cost_file"] = f"{cost_file}"
    inputs["jar_file"] = f"{jar_file}"
    inputs["logging_config"] = f"{logging_config}"
    log.debug(f"inputs: {pformat(inputs)}")

    # TODO: Make arg parsing more generic. For now, only handling latency_success_p99 and percent_fail.
    requirements = {
        Metric.latency_success_p99: [
            Condition(
                lt(latency_success_p99), f"latency_success_p99 < {latency_success_p99}"
            ),
            Condition(gte(Decimal("0")), "latency_success_p99 >= 0"),
        ],
        Metric.percent_fail: [
            Condition(lt(percent_fail), f"percent_fail < {percent_fail}"),
            Condition(gte(Decimal("0")), "percent_fail >= 0"),
        ],
    }
    log.info(f"Starting perfsize with requirements: {requirements}")

    # Track findings for each testing phase
    recommend_type: Dict[str, str] = {}
    recommend_max: Dict[str, str] = {}
    recommend_min: Dict[str, str] = {}

    # Phase 1: Find working instance type.
    # The goal is to find the first instance type that works and how much
    # load it can handle.
    # The count should default to 1, but user might override with a list of
    # higher counts. Final TPS per instance would just need to be calculated
    # accordingly.
    type_plan = Plan(
        parameter_lists={
            Parameter.host: [host],
            Parameter.region: [region],
            Parameter.endpoint_name: [endpoint_name],
            Parameter.endpoint_config_name: [endpoint_config_name],
            Parameter.model_name: [model_name],
            Parameter.instance_type: type_walk,
            Parameter.initial_instance_count: list(map(str, count_walk)),
            Parameter.ramp_start_tps: ["0"],
            Parameter.ramp_minutes: ["0"],
            Parameter.steady_state_tps: list(map(str, tps_walk)),
            Parameter.steady_state_minutes: [f"{duration_minutes}"],
        },
        requirements=requirements,
    )
    log.info(f"Testing instance type with plan: {type_plan}")

    type_workflow = Workflow(
        plan=type_plan,
        step_manager=FirstSuccessStepManager(type_plan),
        environment_manager=SageMakerEnvironmentManager(iam_role_arn, region),
        load_manager=SageMakerLoadManager(
            scenario_requests=scenario_requests,
            gatling_jar_path=jar_file,
            gatling_scenario="GenericSageMakerScenario",
            gatling_results_path=job_id_dir,
            iam_role_arn=iam_role_arn,
            region=region,
        ),
        result_managers=[GatlingResultManager(results_path=job_id_dir)],
        reporters=[MockReporter()],
        teardown_between_steps=False,
        teardown_at_end=True,
    )
    type_recommendation = type_workflow.run()
    log.debug(
        f"Test for instance type got recommendation: {pformat(type_recommendation)}"
    )

    if not type_recommendation:
        print(f"Test failed to find a working instance type from given list.")
        exit(0)  # TODO: replace with return but still generate report

    instance_type = type_recommendation[Parameter.instance_type]
    initial_instance_count = Decimal(
        type_recommendation[Parameter.initial_instance_count]
    )
    steady_state_tps = Decimal(type_recommendation[Parameter.steady_state_tps])
    tps_per_instance = steady_state_tps / initial_instance_count
    recommend_type[Parameter.instance_type] = instance_type
    recommend_type[Parameter.initial_instance_count] = f"{initial_instance_count}"
    recommend_type[Parameter.steady_state_tps] = f"{steady_state_tps}"
    recommend_type["tps_per_instance"] = f"{tps_per_instance}"
    log.info(f"recommend_type: {pformat(recommend_type)}")

    # Phase 2: Find instance count needed for max TPS.
    # Second set limits instance type to the one found above.
    # The goal is to find the number of instances needed to support given
    # peak load. This number is calculated as instance_count_needed,
    # assuming linear extrapolation. But just in case it fails,
    # the test plan includes some endurance_retries.
    instance_count_needed = math.ceil(peak_tps / tps_per_instance)

    max_count_plan = Plan(
        parameter_lists={
            Parameter.host: [host],
            Parameter.region: [region],
            Parameter.endpoint_name: [endpoint_name],
            Parameter.endpoint_config_name: [endpoint_config_name],
            Parameter.model_name: [model_name],
            Parameter.instance_type: [instance_type],
            Parameter.initial_instance_count: list(
                map(
                    str,
                    range(
                        instance_count_needed,
                        instance_count_needed + endurance_retries + 1,
                    ),
                )
            ),
            Parameter.ramp_start_tps: ["0"],
            Parameter.ramp_minutes: ["0"],
            Parameter.steady_state_tps: [f"{peak_tps}"],
            Parameter.steady_state_minutes: [f"{endurance_steady_state_minutes}"],
        },
        requirements=requirements,
    )
    log.info(f"Testing instance count with plan: {max_count_plan}")

    max_count_workflow = Workflow(
        plan=max_count_plan,
        step_manager=FirstSuccessStepManager(max_count_plan),
        environment_manager=SageMakerEnvironmentManager(iam_role_arn, region),
        load_manager=SageMakerLoadManager(
            scenario_requests=scenario_requests,
            gatling_jar_path=jar_file,
            gatling_scenario="GenericSageMakerScenario",
            gatling_results_path=job_id_dir,
            iam_role_arn=iam_role_arn,
            region=region,
        ),
        result_managers=[GatlingResultManager(results_path=job_id_dir)],
        reporters=[MockReporter()],
        teardown_between_steps=True,
        teardown_at_end=True,
    )
    max_count_recommendation = max_count_workflow.run()
    log.debug(
        f"Test for instance count got recommendation: {pformat(max_count_recommendation)}"
    )

    if not max_count_recommendation:
        print(f"Test failed to find a working instance count for peak TPS.")
        exit(0)  # TODO: replace with return but still generate report

    max_instance_count = int(max_count_recommendation[Parameter.initial_instance_count])
    max_steady_state_tps = Decimal(max_count_recommendation[Parameter.steady_state_tps])
    max_tps_per_instance = max_steady_state_tps / max_instance_count
    recommend_max["max_instance_count"] = f"{max_instance_count}"
    recommend_max["max_steady_state_tps"] = f"{max_steady_state_tps}"
    recommend_max["max_tps_per_instance"] = f"{max_tps_per_instance}"
    recommend_max["max_cost"] = cost.explain(instance_type, max_instance_count)
    log.info(f"recommend_max: {pformat(recommend_max)}")

    # Phase 3: Find min instance count that can still support given ramp time.
    # Third set limits instance type and max count to values found above.
    # The goal is to find the number of instances needed to support given
    # ramp from starting TPS to peak TPS over ramp minutes.
    invocations_target = int(
        peak_tps / max_instance_count * 60 * SageMaker.SAFETY_FACTOR
    )

    # TODO: Implement Part 3...
    min_count_plan = None
    log.info(f"Testing min instance count with plan: {min_count_plan}")
    min_count_workflow = None
    min_count_recommendation = None

    recommend_min["min_instance_count"] = "-"  # TODO: implement
    recommend_min["min_cost"] = "-"  # TODO: implement
    recommend_min["invocations_target"] = f"{invocations_target}"
    log.info(f"recommend_min: {pformat(recommend_min)}")

    # Generate final report...
    reporter = HTMLReporter(
        inputs=inputs,
        type_plan=type_plan,
        max_count_plan=max_count_plan,
        min_count_plan=None,
        recommend_type=recommend_type,
        recommend_max=recommend_max,
        recommend_min=recommend_min,
    )
    content = reporter.render()
    report_file = f"{job_id_dir}/Final_Job_Report.html"
    with open(report_file, "w") as file:
        file.write(content)

    # TODO: Add flag to save files to S3...

    log.info(f"See report at {report_file}")


if __name__ == "__main__":
    main()
