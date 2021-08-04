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


class AwsRegion:
    US_EAST_2 = "us-east-2"  # US East (Ohio)
    US_EAST_1 = "us-east-1"  # US East (N. Virginia)
    US_WEST_1 = "us-west-1"  # US West (N. California)
    US_WEST_2 = "us-west-2"  # US West (Oregon)
    AF_SOUTH_1 = "af-south-1"  # Africa (Cape Town)
    AP_EAST_1 = "ap-east-1"  # Asia Pacific (Hong Kong)
    AP_SOUTH_1 = "ap-south-1"  # Asia Pacific (Mumbai)
    AP_NORTHEAST_3 = "ap-northeast-3"  # Asia Pacific (Osaka)
    AP_NORTHEAST_2 = "ap-northeast-2"  # Asia Pacific (Seoul)
    AP_SOUTHEAST_1 = "ap-southeast-1"  # Asia Pacific (Singapore)
    AP_SOUTHEAST_2 = "ap-southeast-2"  # Asia Pacific (Sydney)
    AP_NORTHEAST_1 = "ap-northeast-1"  # Asia Pacific (Tokyo)
    CA_CENTRAL_1 = "ca-central-1"  # Canada (Central)
    EU_CENTRAL_1 = "eu-central-1"  # Europe (Frankfurt)
    EU_WEST_1 = "eu-west-1"  # Europe (Ireland)
    EU_WEST_2 = "eu-west-2"  # Europe (London)
    EU_SOUTH_1 = "eu-south-1"  # Europe (Milan)
    EU_WEST_3 = "eu-west-3"  # Europe (Paris)
    EU_NORTH_1 = "eu-north-1"  # Europe (Stockholm)
    ME_SOUTH_1 = "me-south-1"  # Middle East (Bahrain)
    SA_EAST_1 = "sa-east-1"  # South America (São Paulo)
