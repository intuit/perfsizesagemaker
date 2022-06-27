from datetime import datetime
from decimal import Decimal
import math
from perfsize.perfsize import Condition, Config, Plan, Result, Run, lt, gte
from perfsize.result.gatling import Metric
from perfsizesagemaker.constants import Parameter, SageMaker
from perfsizesagemaker.cost import CostEstimator
from perfsizesagemaker.reporter.html import HTMLReporter
from typing import Dict, List
import pytest


@pytest.fixture
def peak_tps() -> Decimal:
    return Decimal(1000)


@pytest.fixture
def latency_success_p99_requirements() -> List[Condition]:
    return [
        Condition(lt(Decimal("100")), "latency_success_p99 < 100"),
        Condition(gte(Decimal("0")), "latency_success_p99 >= 0"),
    ]


@pytest.fixture
def percent_fail_requirements() -> List[Condition]:
    return [
        Condition(lt(Decimal("0.01")), "percent_fail < 0.01"),
        Condition(gte(Decimal("0")), "percent_fail >= 0"),
    ]


@pytest.fixture
def requirements(
    latency_success_p99_requirements: List[Condition],
    percent_fail_requirements: List[Condition],
) -> Dict[str, List[Condition]]:
    return {
        Metric.latency_success_p99: latency_success_p99_requirements,
        Metric.percent_fail: percent_fail_requirements,
    }


@pytest.fixture
def inputs() -> Dict[str, str]:
    inputs: Dict[str, str] = {}
    inputs["iam_role_arn"] = "arn:aws:iam::123456789012:role/perfsizesagemaker_role"
    inputs["host"] = "runtime.sagemaker.us-west-2.amazonaws.com"
    inputs["region"] = "us-west-2"
    inputs["endpoint_name"] = "LEARNING-model-simulator-1"
    inputs["endpoint_config_name"] = "LEARNING-model-simulator-1-0"
    inputs["variant_name"] = "variant-name-1"
    inputs["model_name"] = "model-simulator"
    inputs[
        "scenario_requests"
    ] = '[{"path":"bodies/model-sim/1/status-200.input.json","weight":100}]'
    inputs["peak_tps"] = "1000"
    inputs["latency_success_p99"] = "100"
    inputs["percent_fail"] = "0.01"
    inputs[
        "type_walk"
    ] = "['ml.m5.large','ml.m5.xlarge','ml.m5.2xlarge','ml.m5.4xlarge']"
    inputs["count_walk"] = "[1]"
    inputs[
        "tps_walk"
    ] = "[Decimal('1'),Decimal('10'),Decimal('100'),Decimal('200'),Decimal('300')]"
    inputs["duration_minutes"] = "5"
    inputs["endurance_ramp_start_tps"] = "0"
    inputs["endurance_ramp_minutes"] = "15"
    inputs["endurance_steady_state_minutes"] = "30"
    inputs["endurance_retries"] = "3"
    inputs["perfsize_results_dir"] = "perfsize-results-dir"
    inputs["job_id_dir"] = "perfsize-results-dir/job-2022-05-01-084016-model-simulator"
    inputs["cost_file"] = "resources/configs/cost/us-west-2.json"
    inputs["jar_file"] = "sagemaker-gatling.jar"
    inputs["logging_config"] = "resources/configs/logging/logging.yml"
    return inputs


@pytest.fixture
def cost() -> CostEstimator:
    # TODO: add region as a parameter... for now, testing with us-west-2
    return CostEstimator("resources/configs/cost/us-west-2.json")


@pytest.fixture
def type_plan(
    requirements: Dict[str, List[Condition]],
    percent_fail_requirements: List[Condition],
    latency_success_p99_requirements: List[Condition],
) -> Plan:
    # Start with test plan to find working instance type.
    type_plan = Plan(
        parameter_lists={
            Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
            Parameter.region: ["us-west-2"],
            Parameter.endpoint_name: ["LEARNING-model-simulator-1"],
            Parameter.endpoint_config_name: ["LEARNING-model-simulator-1-0"],
            Parameter.variant_name: ["variant-name-1"],
            Parameter.model_name: ["model-simulator"],
            Parameter.instance_type: [
                "ml.m5.large",
                "ml.m5.xlarge",
                "ml.m5.2xlarge",
                "ml.m5.4xlarge",
            ],
            Parameter.initial_instance_count: ["1"],
            Parameter.ramp_start_tps: ["0"],
            Parameter.ramp_minutes: ["0"],
            Parameter.steady_state_tps: [
                "1",
                "10",
                "100",
                "200",
                "300",
            ],
            Parameter.steady_state_minutes: ["5"],
        },
        requirements=requirements,
    )
    type_plan.configs = {}
    type_plan.history = []

    # Type config 1 of 5 (omitting other combos to 20)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "1",
            "steady_state_minutes": "5",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651394546-ml.m5.large-1-1TPS",
            start=datetime.strptime("2022-05-01 08:42:30", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 08:47:30", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(metric=Metric.count_success, value=Decimal(300), conditions=[]),
                Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                Result(metric=Metric.count_total, value=Decimal(300), conditions=[]),
                Result(
                    metric=Metric.percent_success, value=Decimal(100), conditions=[]
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal(0),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(15),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(24),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(52),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(56),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(65),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(72),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(74),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(99),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(137),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651394550257),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651394850240),
                    conditions=[],
                ),
            ],
        )
    ]
    type_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "1",
            "0",
            "0",
            "1",
            "5",
        )
    ] = config
    type_plan.history.append(config)

    # Type config 2 of 5 (omitting other combos to 20)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "10",
            "steady_state_minutes": "5",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651394853-ml.m5.large-1-10TPS",
            start=datetime.strptime("2022-05-01 08:47:37", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 08:52:37", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(metric=Metric.count_success, value=Decimal(3000), conditions=[]),
                Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                Result(metric=Metric.count_total, value=Decimal(3000), conditions=[]),
                Result(
                    metric=Metric.percent_success, value=Decimal(100), conditions=[]
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal(0),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(14),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(16),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(32),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(50),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(57),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(64),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(537),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651394857606),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651395157675),
                    conditions=[],
                ),
            ],
        )
    ]
    type_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "1",
            "0",
            "0",
            "10",
            "5",
        )
    ] = config
    type_plan.history.append(config)

    # Type config 3 of 5 (omitting other combos to 20)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "100",
            "steady_state_minutes": "5",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651395164-ml.m5.large-1-100TPS",
            start=datetime.strptime("2022-05-01 08:52:44", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 08:57:44", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(29998), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(2), conditions=[]),
                Result(metric=Metric.count_total, value=Decimal(30000), conditions=[]),
                Result(
                    metric=Metric.percent_success,
                    value=Decimal("99.99333333333333333333333333"),
                    conditions=[],
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal("0.006666666666666666666666666667"),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(7),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(10),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(19),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(26),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1476),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651395164000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651395464000),
                    conditions=[],
                ),
            ],
        )
    ]
    type_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "1",
            "0",
            "0",
            "100",
            "5",
        )
    ] = config
    type_plan.history.append(config)

    # Type config 4 of 5 (omitting other combos to 20)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "200",
            "steady_state_minutes": "5",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651395471-ml.m5.large-1-200TPS",
            start=datetime.strptime("2022-05-01 08:57:51", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 09:02:51", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(59984), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(16), conditions=[]),
                Result(metric=Metric.count_total, value=Decimal(60000), conditions=[]),
                Result(
                    metric=Metric.percent_success,
                    value=Decimal("99.97333333333333333333333333"),
                    conditions=[],
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal("0.02666666666666666666666666667"),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(7),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(10),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(18),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(22),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1882),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651395471000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651395771000),
                    conditions=[],
                ),
            ],
        )
    ]
    type_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "1",
            "0",
            "0",
            "200",
            "5",
        )
    ] = config
    type_plan.history.append(config)

    # Type config 5 of 5 - did not run (omitting other combos to 20)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "300",
            "steady_state_minutes": "5",
        },
        requirements=requirements,
    )
    config.runs = []
    type_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "1",
            "0",
            "0",
            "300",
            "5",
        )
    ] = config

    # Omitting type config 6 through 20 for brevity (all were not run):
    # ml.m5.xlarge: 1, 10, 100, 200, 300 TPS
    # ml.m5.2xlarge: 1, 10, 100, 200, 300 TPS
    # ml.m5.4xlarge: 1, 10, 100, 200, 300 TPS

    type_plan.recommendation = {
        Parameter.host: "runtime.sagemaker.us-west-2.amazonaws.com",
        Parameter.region: "us-west-2",
        Parameter.endpoint_name: "LEARNING-model-simulator-1",
        Parameter.endpoint_config_name: "LEARNING-model-simulator-1-0",
        Parameter.variant_name: "variant-name-1",
        Parameter.model_name: "model-simulator",
        Parameter.instance_type: "ml.m5.large",
        Parameter.initial_instance_count: "1",
        Parameter.ramp_start_tps: "0",
        Parameter.ramp_minutes: "0",
        Parameter.steady_state_tps: "100",
        Parameter.steady_state_minutes: "5",
    }
    return type_plan


@pytest.fixture
def instance_type(type_plan: Plan) -> str:
    return type_plan.recommendation[Parameter.instance_type]


@pytest.fixture
def recommend_type(
    type_plan: Plan, peak_tps: Decimal, instance_type: str
) -> Dict[str, str]:
    recommend_type: Dict[str, str] = {}
    initial_instance_count = Decimal(
        type_plan.recommendation[Parameter.initial_instance_count]
    )
    steady_state_tps = Decimal(type_plan.recommendation[Parameter.steady_state_tps])
    tps_per_instance = steady_state_tps / initial_instance_count
    recommend_type[Parameter.instance_type] = instance_type
    recommend_type[Parameter.initial_instance_count] = f"{initial_instance_count}"
    recommend_type[Parameter.steady_state_tps] = f"{steady_state_tps}"
    recommend_type["tps_per_instance"] = f"{tps_per_instance}"
    instance_count_needed = math.ceil(peak_tps / tps_per_instance)
    recommend_type["instance_count_needed"] = f"{instance_count_needed}"
    recommend_type["explanation"] = (
        f"Last green run was {steady_state_tps} TPS supported by {initial_instance_count} instances of {instance_type}.\n"
        f"{steady_state_tps} / {initial_instance_count} = {tps_per_instance} TPS per instance.\n"
        f"To support {peak_tps} TPS, we need ceiling({peak_tps} / {tps_per_instance}) = {instance_count_needed} instances."
    )
    return recommend_type


@pytest.fixture
def max_count_plan(
    peak_tps: Decimal,
    requirements: Dict[str, List[Condition]],
    percent_fail_requirements: List[Condition],
    latency_success_p99_requirements: List[Condition],
) -> Plan:
    # Next is test plan to find max instance count needed for peak TPS.
    max_count_plan = Plan(
        parameter_lists={
            Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
            Parameter.region: ["us-west-2"],
            Parameter.endpoint_name: ["LEARNING-model-simulator-1"],
            Parameter.endpoint_config_name: ["LEARNING-model-simulator-1-0"],
            Parameter.variant_name: ["variant-name-1"],
            Parameter.model_name: ["model-simulator"],
            Parameter.instance_type: ["ml.m5.large"],
            Parameter.initial_instance_count: ["10", "11", "12", "13"],
            Parameter.ramp_start_tps: ["0"],
            Parameter.ramp_minutes: ["0"],
            Parameter.steady_state_tps: [f"{peak_tps}"],
            Parameter.steady_state_minutes: ["30"],
        },
        requirements=requirements,
    )
    max_count_plan.configs = {}
    max_count_plan.history = []

    # Max count config 1 (omitting other combos to 4)
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "10",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "1000",
            "steady_state_minutes": "30",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651395951-ml.m5.large-10-1000TPS",
            start=datetime.strptime("2022-05-01 09:05:51", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 09:35:51", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(1800000), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                Result(
                    metric=Metric.count_total, value=Decimal(1800000), conditions=[]
                ),
                Result(
                    metric=Metric.percent_success, value=Decimal(100), conditions=[]
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal(0),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(7),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(10),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(16),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(22),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(31),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1884),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651395951000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651397751000),
                    conditions=[],
                ),
            ],
        )
    ]
    max_count_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            "10",
            "0",
            "0",
            "1000",
            "30",
        )
    ] = config
    max_count_plan.history.append(config)

    # Omitting max config 2 through 4 for brevity (all were not run):
    # ml.m5.large, 11 instances, 1000 TPS
    # ml.m5.large, 12 instances, 1000 TPS
    # ml.m5.large, 13 instances, 1000 TPS
    return max_count_plan


@pytest.fixture
def max_instance_count() -> int:
    return 10


@pytest.fixture
def invocations_target(peak_tps: Decimal, max_instance_count: int) -> int:
    return int(peak_tps / max_instance_count * 60 * SageMaker.SAFETY_FACTOR)


@pytest.fixture
def recommend_max(
    peak_tps: Decimal,
    max_instance_count: int,
    instance_type: str,
    invocations_target: int,
    cost: CostEstimator,
) -> Dict[str, str]:
    recommend_max: Dict[str, str] = {}

    max_steady_state_tps = peak_tps
    max_tps_per_instance = max_steady_state_tps / max_instance_count

    recommend_max["max_instance_count"] = f"{max_instance_count}"
    recommend_max["max_steady_state_tps"] = f"{max_steady_state_tps}"
    recommend_max["max_tps_per_instance"] = f"{max_tps_per_instance}"
    recommend_max["max_cost"] = cost.explain(instance_type, max_instance_count)
    recommend_max["invocations_target"] = f"{invocations_target}"
    recommend_max["explanation"] = (
        f"Last green run was {max_steady_state_tps} TPS supported by {max_instance_count} instances of {instance_type}.\n"
        f"max_tps_per_instance = {max_steady_state_tps} / {max_instance_count} = {max_tps_per_instance} TPS per instance.\n"
        f"Autoscaling metric (SageMakerVariantInvocationsPerInstance):\n"
        f"= int(max_tps_per_instance * 60 seconds/minute * safety_factor)\n"
        f"= int({max_tps_per_instance} * 60 * {SageMaker.SAFETY_FACTOR})\n"
        f"= {invocations_target} invocations / instance / minute"
    )
    return recommend_max


@pytest.fixture
def min_count_plan(
    max_instance_count: int,
    invocations_target: int,
    peak_tps: Decimal,
    requirements: Dict[str, List[Condition]],
    percent_fail_requirements: List[Condition],
    latency_success_p99_requirements: List[Condition],
) -> Plan:
    # Next is test plan to find min instance count needed for autoscaling.
    min_count_plan = Plan(
        parameter_lists={
            Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
            Parameter.region: ["us-west-2"],
            Parameter.endpoint_name: ["LEARNING-model-simulator-1"],
            Parameter.endpoint_config_name: ["LEARNING-model-simulator-1-0"],
            Parameter.variant_name: ["variant-name-1"],
            Parameter.model_name: ["model-simulator"],
            Parameter.instance_type: ["ml.m5.large"],
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
            Parameter.ramp_start_tps: ["0"],
            Parameter.ramp_minutes: ["15"],
            Parameter.steady_state_tps: [f"{peak_tps}"],
            Parameter.steady_state_minutes: ["30"],
        },
        requirements=requirements,
    )
    min_count_plan.configs = {}
    min_count_plan.history = []

    # Min count config 1 - try min5 max10 - failed
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            # omitting "initial_instance_count"
            "scaling_enabled": "True",
            "scaling_min_instance_count": "5",
            "scaling_max_instance_count": "10",
            "scaling_metric": "SageMakerVariantInvocationsPerInstance",
            "scaling_target": "3000",
            "ramp_start_tps": "0",
            "ramp_minutes": "15",
            "steady_state_tps": "1000",
            "steady_state_minutes": "30",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651399200-ml.m5.large-min5-max10-1000TPS",
            start=datetime.strptime("2022-05-01 10:00:00", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 10:45:00", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(2248102), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(1898), conditions=[]),
                Result(
                    metric=Metric.count_total, value=Decimal(2250000), conditions=[]
                ),
                Result(
                    metric=Metric.percent_success,
                    value=Decimal("99.915644444444444"),
                    conditions=[],
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal("0.084355555555556"),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(6),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(19),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(22),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(143),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1495),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651399200000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651401900000),
                    conditions=[],
                ),
            ],
        )
    ]
    min_count_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            # omitting "initial_instance_count"
            "True",
            "5",
            "10",
            "SageMakerVariantInvocationsPerInstance",
            "3000",
            "0",
            "15",
            "1000",
            "30",
        )
    ] = config
    min_count_plan.history.append(config)

    # Min count config 2 - try min7 max10 - passed
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            # omitting "initial_instance_count"
            "scaling_enabled": "True",
            "scaling_min_instance_count": "7",
            "scaling_max_instance_count": "10",
            "scaling_metric": "SageMakerVariantInvocationsPerInstance",
            "scaling_target": "3000",
            "ramp_start_tps": "0",
            "ramp_minutes": "15",
            "steady_state_tps": "1000",
            "steady_state_minutes": "30",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651402800-ml.m5.large-min7-max10-1000TPS",
            start=datetime.strptime("2022-05-01 11:00:00", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 11:45:00", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(2249880), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(120), conditions=[]),
                Result(
                    metric=Metric.count_total, value=Decimal(2250000), conditions=[]
                ),
                Result(
                    metric=Metric.percent_success,
                    value=Decimal("99.994666666666667"),
                    conditions=[],
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal("0.005333333333333"),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(7),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(16),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(22),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(36),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1521),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651402800000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651405500000),
                    conditions=[],
                ),
            ],
        )
    ]
    min_count_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            # omitting "initial_instance_count"
            "True",
            "7",
            "10",
            "SageMakerVariantInvocationsPerInstance",
            "3000",
            "0",
            "15",
            "1000",
            "30",
        )
    ] = config
    min_count_plan.history.append(config)

    # Min count config 3 - try min6 max10 - failed
    config = Config(
        parameters={
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "variant_name": "variant-name-1",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            # omitting "initial_instance_count"
            "scaling_enabled": "True",
            "scaling_min_instance_count": "6",
            "scaling_max_instance_count": "10",
            "scaling_metric": "SageMakerVariantInvocationsPerInstance",
            "scaling_target": "3000",
            "ramp_start_tps": "0",
            "ramp_minutes": "15",
            "steady_state_tps": "1000",
            "steady_state_minutes": "30",
        },
        requirements=requirements,
    )
    config.runs = [
        Run(
            id="1651406400-ml.m5.large-min6-max10-1000TPS",
            start=datetime.strptime("2022-05-01 12:00:00", "%Y-%m-%d %H:%M:%S"),
            end=datetime.strptime("2022-05-01 12:45:00", "%Y-%m-%d %H:%M:%S"),
            results=[
                Result(
                    metric=Metric.count_success, value=Decimal(2249407), conditions=[]
                ),
                Result(metric=Metric.count_fail, value=Decimal(593), conditions=[]),
                Result(
                    metric=Metric.count_total, value=Decimal(2250000), conditions=[]
                ),
                Result(
                    metric=Metric.percent_success,
                    value=Decimal("99.973644444444444"),
                    conditions=[],
                ),
                Result(
                    metric=Metric.percent_fail,
                    value=Decimal("0.026355555555556"),
                    conditions=percent_fail_requirements,
                ),
                Result(
                    metric=Metric.latency_success_min,
                    value=Decimal(6),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p25,
                    value=Decimal(9),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p50,
                    value=Decimal(11),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p75,
                    value=Decimal(12),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p90,
                    value=Decimal(13),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p95,
                    value=Decimal(18),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p98,
                    value=Decimal(22),
                    conditions=[],
                ),
                Result(
                    metric=Metric.latency_success_p99,
                    value=Decimal(65),
                    conditions=latency_success_p99_requirements,
                ),
                Result(
                    metric=Metric.latency_success_max,
                    value=Decimal(1701),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_start,
                    value=Decimal(1651406400000),
                    conditions=[],
                ),
                Result(
                    metric=Metric.simulation_end,
                    value=Decimal(1651409100000),
                    conditions=[],
                ),
            ],
        )
    ]
    min_count_plan.configs[
        (
            "runtime.sagemaker.us-west-2.amazonaws.com",
            "us-west-2",
            "LEARNING-model-simulator-1",
            "LEARNING-model-simulator-1-0",
            "variant-name-1",
            "model-simulator",
            "ml.m5.large",
            # omitting "initial_instance_count"
            "True",
            "6",
            "10",
            "SageMakerVariantInvocationsPerInstance",
            "3000",
            "0",
            "15",
            "1000",
            "30",
        )
    ] = config
    min_count_plan.history.append(config)
    return min_count_plan


@pytest.fixture
def recommend_min(
    invocations_target: int,
    cost: CostEstimator,
    instance_type: str,
    max_instance_count: int,
) -> Dict[str, str]:
    recommend_min: Dict[str, str] = {}
    min_instance_count = 7
    scaling_metric = "SageMakerVariantInvocationsPerInstance"
    scaling_target = f"{invocations_target}"
    ramp_start_tps = "0"
    ramp_minutes = "15"
    steady_state_tps = "1000"
    steady_state_minutes = "30"
    recommend_min["min_instance_count"] = str(min_instance_count)
    recommend_min["min_cost"] = cost.explain(instance_type, min_instance_count)
    recommend_min["explanation"] = (
        f"Traffic was {ramp_start_tps} TPS ramped over {ramp_minutes} minutes to {steady_state_tps} TPS, and then run for {steady_state_minutes} minutes.\n"
        f"Last green run was auto scale configuration with minimum {min_instance_count}, maximum {max_instance_count} instances of type {instance_type},\n"
        f"with scaling metric {scaling_metric} at {scaling_target} as calculated earlier.\n"
    )
    return recommend_min


class TestHTMLReporter:
    def test_render_all_tests_pass(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=max_count_plan,
            min_count_plan=min_count_plan,
            recommend_type=recommend_type,
            recommend_max=recommend_max,
            recommend_min=recommend_min,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
        summary = (
            "Success! Based on the provided inputs, here are the "
            "suggested settings for deploying model-simulator with either "
            "fixed scale or auto scale."
        )
        assert summary in content

    def test_render_auto_scale_failed(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=max_count_plan,
            min_count_plan=min_count_plan,
            recommend_type=recommend_type,
            recommend_max=recommend_max,
            recommend_min=None,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #    file.write(content)
        summary = (
            "Success! Based on the provided inputs, here are the "
            "suggested settings for deploying model-simulator with fixed "
            "scale. But for auto scale, the tests were either skipped "
            "or failed."
        )
        assert summary in content
        # No final auto scale recommendation, but tests were still attempted.
        # Ignore placeholder values from test fixture data though, since those
        # were populated for the successful case.
        text = (
            "Instance Type and Auto Scale (left column) vs. Traffic Pattern (top row):"
        )
        assert text in content
        text = "ERROR: Endurance tests using given ramp traffic pattern failed to meet SLA rules."
        assert text in content

    def test_render_auto_scale_skipped(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=max_count_plan,
            min_count_plan=None,
            recommend_type=recommend_type,
            recommend_max=recommend_max,
            recommend_min=None,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
        summary = (
            "Success! Based on the provided inputs, here are the "
            "suggested settings for deploying model-simulator with fixed "
            "scale. But for auto scale, the tests were either skipped "
            "or failed."
        )
        assert summary in content
        # In this case, the auto scale testing section was skipped altogether.
        text = (
            "This section was skipped either by configuration, or due to above errors."
        )
        assert text in content

    def test_render_endurance_failed(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=max_count_plan,
            min_count_plan=None,
            recommend_type=recommend_type,
            recommend_max=None,
            recommend_min=None,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
        summary = (
            "Failure! Found instance type ml.m5.large worked for type tests, "
            "but endurance tests failed."
        )
        assert summary in content
        text = "ERROR: Endurance tests failed to meet SLA rules."
        assert text in content

    def test_render_endurance_skipped(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=None,
            min_count_plan=None,
            recommend_type=recommend_type,
            recommend_max=None,
            recommend_min=None,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
        summary = (
            "Failure! Found instance type ml.m5.large worked for type tests, "
            "but endurance tests failed."
        )
        assert summary in content
        text = (
            "This section was skipped either by configuration, or due to above errors."
        )
        assert text in content

    def test_render_type_failed(
        self,
        inputs: Dict[str, str],
        type_plan: Plan,
        max_count_plan: Plan,
        min_count_plan: Plan,
        recommend_type: Dict[str, str],
        recommend_max: Dict[str, str],
        recommend_min: Dict[str, str],
    ) -> None:
        reporter = HTMLReporter(
            inputs=inputs,
            type_plan=type_plan,
            max_count_plan=None,
            min_count_plan=None,
            recommend_type=None,
            recommend_max=None,
            recommend_min=None,
        )
        content = reporter.render()
        # Uncomment for debugging...
        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
        summary = "Failure! No solution found given inputs below."
        assert summary in content
