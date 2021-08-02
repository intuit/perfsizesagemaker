from decimal import Decimal
from perfsize.perfsize import (
    Condition,
    gte,
    lt,
    Plan,
    Workflow,
)
from perfsize.environment.mock import MockEnvironmentManager
from perfsize.load.mock import MockLoadManager
from perfsize.reporter.mock import MockReporter
from perfsize.result.mock import MockResultManager
from perfsizesagemaker.constants import Parameter
from perfsizesagemaker.step.sagemaker import FirstSuccessStepManager
import pytest


@pytest.fixture
def sample_plan() -> Plan:
    return Plan(
        parameter_lists={
            Parameter.host: ["runtime.sagemaker.us-west-2.amazonaws.com"],
            Parameter.region: ["us-west-2"],
            Parameter.endpoint_name: ["LEARNING-model-simulator-1"],
            Parameter.endpoint_config_name: ["LEARNING-model-simulator-1-0"],
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
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "10",
                "20",
                "30",
                "40",
                "50",
                "60",
                "70",
                "80",
                "90",
                "100",
                "200",
                "300",
                "400",
            ],
            Parameter.steady_state_minutes: ["3"],
        },
        requirements={
            "latency_success_p99": [
                Condition(lt(Decimal("200")), "value < 200"),
                Condition(gte(Decimal("0")), "value >= 0"),
            ],
            "percent_fail": [
                Condition(lt(Decimal("0.01")), "value < 0.01"),
                Condition(gte(Decimal("0")), "value >= 0"),
            ],
        },
    )


class TestFirstSuccessStepManager:
    def test_plan(self, sample_plan: Plan) -> None:
        workflow = Workflow(
            plan=sample_plan,
            step_manager=FirstSuccessStepManager(sample_plan),
            environment_manager=MockEnvironmentManager(),
            load_manager=MockLoadManager(),
            result_managers=[MockResultManager()],
            reporters=[MockReporter()],
        )
        recommendation = workflow.run()
        assert len(sample_plan.history) == 22
        assert recommendation == {
            "host": "runtime.sagemaker.us-west-2.amazonaws.com",
            "region": "us-west-2",
            "endpoint_name": "LEARNING-model-simulator-1",
            "endpoint_config_name": "LEARNING-model-simulator-1-0",
            "model_name": "model-simulator",
            "instance_type": "ml.m5.large",
            "initial_instance_count": "1",
            "ramp_start_tps": "0",
            "ramp_minutes": "0",
            "steady_state_tps": "400",
            "steady_state_minutes": "3",
        }
