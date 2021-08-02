from decimal import Decimal


class Parameter:
    host = "host"
    region = "region"
    endpoint_name = "endpoint_name"
    endpoint_config_name = "endpoint_config_name"
    model_name = "model_name"
    instance_type = "instance_type"
    initial_instance_count = "initial_instance_count"
    ramp_start_tps = "ramp_start_tps"
    ramp_minutes = "ramp_minutes"
    steady_state_tps = "steady_state_tps"
    steady_state_minutes = "steady_state_minutes"


class SageMaker:
    SAFETY_FACTOR = Decimal("0.5")
