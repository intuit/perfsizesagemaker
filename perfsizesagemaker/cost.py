from decimal import Decimal
import json


class CostEstimator:

    # TODO: Add step to download latest prices from online...
    # TODO: Add region as a parameter...
    # For now, using local file passed in

    def __init__(self, cost_file: str):
        self.rates = json.loads(open(cost_file, "r").read())

    def explain(self, instance_type: str, instance_count: int) -> str:
        if instance_type not in self.rates:
            return f"ERROR: Cost lookup did not find type {instance_type}"
        single = Decimal(str(self.rates[instance_type]))
        instance = "instance" if instance_count == 1 else "instances"
        explanation = (
            f"{instance_count} {instance} of {instance_type} at ${single}/hour:\n"
        )
        hourly = instance_count * single
        explanation += (
            f"hourly = {instance_count} {instance} * {single}/hour = ${hourly}/hour\n"
        )
        daily = 24 * hourly
        explanation += f"daily = 24 hours * {hourly}/hour = ${daily}/day\n"
        monthly = 30 * daily
        explanation += f"monthly = 30 days * {daily}/day = ${monthly}/month\n"
        annual = 365 * daily
        explanation += f"annual = 365 days * {daily}/day = ${annual}/year\n"
        return explanation
