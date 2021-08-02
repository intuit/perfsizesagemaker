from perfsizesagemaker.cost import CostEstimator
import pytest


class TestCostEstimator:
    sample_costs = [
        (
            "ml.m5.large",
            1,
            "$0.115/hour",
            "$2.760/day",
            "$82.800/month",
            "$1007.400/year",
        ),
        (
            "ml.m5.large",
            2,
            "$0.230/hour",
            "$5.520/day",
            "$165.600/month",
            "$2014.800/year",
        ),
        (
            "ml.m5.large",
            3,
            "$0.345/hour",
            "$8.280/day",
            "$248.400/month",
            "$3022.200/year",
        ),
        (
            "ml.m5.xlarge",
            1,
            "$0.23/hour",
            "$5.52/day",
            "$165.60/month",
            "$2014.80/year",
        ),
        (
            "ml.m5.xlarge",
            2,
            "$0.46/hour",
            "$11.04/day",
            "$331.20/month",
            "$4029.60/year",
        ),
        (
            "ml.m5.xlarge",
            3,
            "$0.69/hour",
            "$16.56/day",
            "$496.80/month",
            "$6044.40/year",
        ),
    ]

    @pytest.mark.parametrize(
        "instance_type, instance_count, hour, day, month, year", sample_costs
    )
    def test_explain(
        self,
        instance_type: str,
        instance_count: int,
        hour: str,
        day: str,
        month: str,
        year: str,
    ) -> None:
        cost = CostEstimator("configs/cost/us-west-2.json")
        explanation = cost.explain(instance_type, instance_count)
        print(explanation)
        assert hour in explanation
        assert day in explanation
        assert month in explanation
        assert year in explanation

    def test_explain_lookup_fail(self) -> None:
        cost = CostEstimator("configs/cost/us-west-2.json")
        explanation = cost.explain("ml.m5.invalid", 1)
        print(explanation)
        assert explanation == "ERROR: Cost lookup did not find type ml.m5.invalid"
