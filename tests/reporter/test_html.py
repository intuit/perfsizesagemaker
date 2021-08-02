from datetime import datetime
from decimal import Decimal
import math
from perfsize.perfsize import Condition, Config, Plan, Result, Run, lt, gte
from perfsize.result.gatling import Metric
from perfsizesagemaker.constants import Parameter, SageMaker
from perfsizesagemaker.cost import CostEstimator
from perfsizesagemaker.reporter.html import HTMLReporter
from pprint import pformat
from typing import Dict


class TestHTMLReporter:
    def test_render(self) -> None:

        # Simulate workflow inputs and results
        peak_tps = Decimal(10)
        latency_success_p99_requirements = [
            Condition(lt(Decimal("400")), "latency_success_p99 < 400"),
            Condition(gte(Decimal("0")), "latency_success_p99 >= 0"),
        ]
        percent_fail_requirements = [
            Condition(lt(Decimal("0.01")), "percent_fail < 0.01"),
            Condition(gte(Decimal("0")), "percent_fail >= 0"),
        ]
        requirements = {
            Metric.latency_success_p99: latency_success_p99_requirements,
            Metric.percent_fail: percent_fail_requirements,
        }

        inputs: Dict[str, str] = {}
        inputs[
            "iam_role_arn"
        ] = "arn:aws:iam::733536204770:role/machine-learning-platform-prd-jenkins"
        inputs["host"] = "runtime.sagemaker.us-west-2.amazonaws.com"
        inputs["region"] = "us-west-2"
        inputs["endpoint_name"] = "LEARNING-model-sim-public-1"
        inputs["endpoint_config_name"] = "LEARNING-model-sim-public-1-0"
        inputs["model_name"] = "model-sim-public"
        inputs[
            "scenario_requests"
        ] = '[{"path":"bodies/model-sim/1/status-200.input.json","weight":100}]'
        inputs["peak_tps"] = "10"
        inputs["latency_success_p99"] = "400"
        inputs["percent_fail"] = "0.01"
        inputs[
            "type_walk"
        ] = '["ml.m5.large","ml.m5.xlarge","ml.m5.2xlarge","ml.m5.4xlarge"]'
        inputs["count_walk"] = '["1"]'
        inputs["tps_walk"] = '["1","10","100"]'
        inputs["duration_minutes"] = "1"
        inputs["endurance_ramp_start_tps"] = "0"
        inputs["endurance_ramp_minutes"] = "0"
        inputs["endurance_steady_state_minutes"] = "1"
        inputs["endurance_retries"] = "3"
        inputs["perfsize_results_dir"] = "perfsize-results-dir"
        inputs[
            "job_id_dir"
        ] = "perfsize-results-dir/job-2021-07-13-0117-model-sim-public"
        print(f"inputs: {pformat(inputs)}")

        # Track findings for each testing phase
        recommend_type: Dict[str, str] = {}
        recommend_max: Dict[str, str] = {}
        recommend_min: Dict[str, str] = {}

        # TODO: add region as a parameter... for now, testing with us-west-2
        cost = CostEstimator("configs/cost/us-west-2.json")

        # Start with test plan to find working instance type.
        type_plan = Plan(
            parameter_lists={
                Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
                Parameter.region: ["us-west-2"],
                Parameter.endpoint_name: ["LEARNING-model-sim-public-1"],
                Parameter.endpoint_config_name: ["LEARNING-model-sim-public-1-0"],
                Parameter.model_name: ["model-sim-public"],
                Parameter.instance_type: [
                    "ml.m5.large",
                    "ml.m5.xlarge",
                    "ml.m5.2xlarge",
                    "ml.m5.4xlarge",
                ],
                Parameter.initial_instance_count: ["1"],
                Parameter.ramp_start_tps: ["0"],
                Parameter.ramp_minutes: ["0"],
                Parameter.steady_state_tps: ["1", "10", "100",],
                Parameter.steady_state_minutes: ["1"],
            },
            requirements=requirements,
        )
        type_plan.configs = {}
        type_plan.history = []

        # Type config 1 of 6
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "1",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = [
            Run(
                id="1622790319-ml.m5.large-1-1TPS",
                start=datetime.strptime("2021-06-04 07:05:19", "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime("2021-06-04 07:06:23", "%Y-%m-%d %H:%M:%S"),
                results=[
                    Result(
                        metric=Metric.count_success, value=Decimal(60), conditions=[]
                    ),
                    Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                    Result(metric=Metric.count_total, value=Decimal(60), conditions=[]),
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
                        value=Decimal(100),
                        conditions=latency_success_p99_requirements,
                    ),
                    Result(
                        metric=Metric.latency_success_max,
                        value=Decimal(137),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_start,
                        value=Decimal(1622790323660),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_end,
                        value=Decimal(1622790382662),
                        conditions=[],
                    ),
                ],
            )
        ]
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "1",
                "0",
                "0",
                "1",
                "1",
            )
        ] = config
        type_plan.history.append(config)

        # Type config 2 of 6
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = [
            Run(
                id="1622790384-ml.m5.large-1-10TPS",
                start=datetime.strptime("2021-06-04 07:06:24", "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime("2021-06-04 07:07:28", "%Y-%m-%d %H:%M:%S"),
                results=[
                    Result(
                        metric=Metric.count_success, value=Decimal(600), conditions=[]
                    ),
                    Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                    Result(
                        metric=Metric.count_total, value=Decimal(600), conditions=[]
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
                        value=Decimal(1622790388054),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_end,
                        value=Decimal(1622790447949),
                        conditions=[],
                    ),
                ],
            )
        ]
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "1",
                "0",
                "0",
                "10",
                "1",
            )
        ] = config
        type_plan.history.append(config)

        # Type config 3 of 6
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "100",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = [
            Run(
                id="1622790449-ml.m5.large-1-100TPS",
                start=datetime.strptime("2021-06-04 07:07:29", "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime("2021-06-04 07:08:35", "%Y-%m-%d %H:%M:%S"),
                results=[
                    Result(
                        metric=Metric.count_success, value=Decimal(6000), conditions=[]
                    ),
                    Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                    Result(
                        metric=Metric.count_total, value=Decimal(6000), conditions=[]
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
                        value=Decimal(8),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p25,
                        value=Decimal(10),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p50,
                        value=Decimal(11),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p75,
                        value=Decimal(11),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p90,
                        value=Decimal(13),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p95,
                        value=Decimal(14),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p98,
                        value=Decimal(22),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p99,
                        value=Decimal(25),
                        conditions=latency_success_p99_requirements,
                    ),
                    Result(
                        metric=Metric.latency_success_max,
                        value=Decimal(1026),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_start,
                        value=Decimal(1622790453538),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_end,
                        value=Decimal(1622790514030),
                        conditions=[],
                    ),
                ],
            )
        ]
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "1",
                "0",
                "0",
                "100",
                "1",
            )
        ] = config
        type_plan.history.append(config)

        # Type config 4 of 6 - did not run
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.xlarge",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "1",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = []
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.xlarge",
                "1",
                "0",
                "0",
                "1",
                "1",
            )
        ] = config

        # Type config 5 of 6 - did not run
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.xlarge",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = []
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.xlarge",
                "1",
                "0",
                "0",
                "10",
                "1",
            )
        ] = config

        # Type config 6 of 6 - did not run
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.xlarge",
                "initial_instance_count": "1",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "100",
                "steady_state_minutes": "1",
            },
            requirements=requirements,
        )
        config.runs = []
        type_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.xlarge",
                "1",
                "0",
                "0",
                "100",
                "1",
            )
        ] = config

        type_plan.recommendation = {
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-sim-public-1",
            "endpoint_config_name": "LEARNING-model-sim-public-1-0",
            "model_name": "model-sim-public",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "100",
            "steady_state_minutes": "1",
        }

        # Next is test plan to find max instance count needed for peak TPS.
        instance_type = type_plan.recommendation[Parameter.instance_type]
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

        max_count_plan = Plan(
            parameter_lists={
                Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
                Parameter.region: ["us-west-2"],
                Parameter.endpoint_name: ["LEARNING-model-sim-public-1"],
                Parameter.endpoint_config_name: ["LEARNING-model-sim-public-1-0"],
                Parameter.model_name: ["model-sim-public"],
                Parameter.instance_type: ["ml.m5.large"],
                Parameter.initial_instance_count: ["2", "3", "4", "5"],
                Parameter.ramp_start_tps: ["0"],
                Parameter.ramp_minutes: ["0"],
                Parameter.steady_state_tps: [f"{peak_tps}"],
                Parameter.steady_state_minutes: ["30"],
            },
            requirements=requirements,
        )
        max_count_plan.configs = {}
        max_count_plan.history = []

        # Max count config 1 of 4
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "2",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "30",
            },
            requirements=requirements,
        )
        config.runs = [
            Run(
                id="1622790540-ml.m5.large-2-10TPS",
                start=datetime.strptime("2021-06-04 07:09:00", "%Y-%m-%d %H:%M:%S"),
                end=datetime.strptime("2021-06-04 07:39:00", "%Y-%m-%d %H:%M:%S"),
                results=[
                    Result(
                        metric=Metric.count_success, value=Decimal(18000), conditions=[]
                    ),
                    Result(metric=Metric.count_fail, value=Decimal(0), conditions=[]),
                    Result(
                        metric=Metric.count_total, value=Decimal(18000), conditions=[]
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
                        value=Decimal(16),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p25,
                        value=Decimal(25),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p50,
                        value=Decimal(53),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p75,
                        value=Decimal(57),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p90,
                        value=Decimal(66),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p95,
                        value=Decimal(73),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p98,
                        value=Decimal(75),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.latency_success_p99,
                        value=Decimal(101),
                        conditions=latency_success_p99_requirements,
                    ),
                    Result(
                        metric=Metric.latency_success_max,
                        value=Decimal(138),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_start,
                        value=Decimal(1622790540000),
                        conditions=[],
                    ),
                    Result(
                        metric=Metric.simulation_end,
                        value=Decimal(1622792340000),
                        conditions=[],
                    ),
                ],
            )
        ]
        max_count_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "2",
                "0",
                "0",
                "10",
                "30",
            )
        ] = config
        max_count_plan.history.append(config)

        # Max count config 2 of 4
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "3",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "30",
            },
            requirements=requirements,
        )
        config.runs = []
        max_count_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "3",
                "0",
                "0",
                "10",
                "30",
            )
        ] = config

        # Max count config 3 of 4
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "4",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "30",
            },
            requirements=requirements,
        )
        config.runs = []
        max_count_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "4",
                "0",
                "0",
                "10",
                "30",
            )
        ] = config

        # Max count config 4 of 4
        config = Config(
            parameters={
                "host": "runtime.sagemaker.us-west-2.amazonaws.com",
                "region": "us-west-2",
                "endpoint_name": "LEARNING-model-sim-public-1",
                "endpoint_config_name": "LEARNING-model-sim-public-1-0",
                "model_name": "model-sim-public",
                "instance_type": "ml.m5.large",
                "initial_instance_count": "5",
                "ramp_start_tps": "0",
                "ramp_minutes": "0",
                "steady_state_tps": "10",
                "steady_state_minutes": "30",
            },
            requirements=requirements,
        )
        config.runs = []
        max_count_plan.configs[
            (
                "runtime.sagemaker.us-west-2.amazonaws.com",
                "us-west-2",
                "LEARNING-model-sim-public-1",
                "LEARNING-model-sim-public-1-0",
                "model-sim-public",
                "ml.m5.large",
                "5",
                "0",
                "0",
                "10",
                "30",
            )
        ] = config

        max_instance_count = 2
        recommend_max["max_instance_count"] = f"{max_instance_count}"
        recommend_max["max_steady_state_tps"] = "10"
        recommend_max["max_tps_per_instance"] = "5"
        recommend_max["max_cost"] = cost.explain(instance_type, max_instance_count)

        # Next is test plan to find min instance count needed for autoscaling.
        invocations_target = int(
            peak_tps / max_instance_count * 60 * SageMaker.SAFETY_FACTOR
        )

        # TODO: Implement testing process to determine min count for autoscaling...
        # min_count_plan = None
        # min_count_workflow = None
        # min_count_recommendation = None

        recommend_min["min_instance_count"] = "-"  # TODO: implement
        recommend_min["min_cost"] = "-"  # TODO: implement
        recommend_min["invocations_target"] = f"{invocations_target}"

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
        success = "Success! Based on the provided inputs, here are the suggested settings for deploying model-sim-public."
        assert success in content

        # with open(f"Final_Job_Report.html", "w") as file:
        #     file.write(content)
