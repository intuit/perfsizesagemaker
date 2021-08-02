from typing import Optional
from perfsize.perfsize import (
    Config,
    Plan,
    StepManager,
)
from perfsizesagemaker.constants import Parameter


class FirstSuccessStepManager(StepManager):
    def __init__(self, plan: Plan) -> None:
        super().__init__(plan)
        assert len(plan.parameter_lists[Parameter.host]) == 1
        self.host = plan.parameter_lists[Parameter.host][0]

        assert len(plan.parameter_lists[Parameter.region]) == 1
        self.region = plan.parameter_lists[Parameter.region][0]

        assert len(plan.parameter_lists[Parameter.endpoint_name]) == 1
        self.endpoint_name = plan.parameter_lists[Parameter.endpoint_name][0]

        assert len(plan.parameter_lists[Parameter.endpoint_config_name]) == 1
        self.endpoint_config_name = plan.parameter_lists[
            Parameter.endpoint_config_name
        ][0]

        assert len(plan.parameter_lists[Parameter.model_name]) == 1
        self.model_name = plan.parameter_lists[Parameter.model_name][0]

        self.instance_type_list = plan.parameter_lists[Parameter.instance_type]
        self.instance_type_index = 0

        self.initial_instance_count_list = plan.parameter_lists[
            Parameter.initial_instance_count
        ]
        self.initial_instance_count_index = 0

        assert len(plan.parameter_lists[Parameter.ramp_start_tps]) == 1
        self.ramp_start_tps = plan.parameter_lists[Parameter.ramp_start_tps][0]

        assert len(plan.parameter_lists[Parameter.ramp_minutes]) == 1
        self.ramp_minutes = plan.parameter_lists[Parameter.ramp_minutes][0]

        self.steady_state_tps_list = plan.parameter_lists[Parameter.steady_state_tps]
        self.steady_state_tps_index = 0

        assert len(plan.parameter_lists[Parameter.steady_state_minutes]) == 1
        self.steady_state_minutes = plan.parameter_lists[
            Parameter.steady_state_minutes
        ][0]

        self.found_success = False

    def next(self) -> Optional[Config]:
        # Start from lowest TPS on lowest instance type and count combination.
        # While failure, keep trying next higher type and count combination.
        # On success, we have found a working type and count combination,
        # so stay with this combination. But keep trying higher TPS until next
        # failure, then go with highest TPS achieved on this combination.

        if not self.plan.history:
            # No tests run yet, so proceed with index values at 0
            pass
        else:
            # Check most recent run
            previous_config = self.plan.history[-1]
            previous_run = previous_config.runs[-1]
            if previous_run.status:
                self.found_success = True
                self.plan.recommendation = previous_config.parameters

            # Determine next step
            if self.found_success:
                # If most recent run failed, but already have prior success, stop.
                if not previous_run.status:
                    return None
                # Stay with current type and count config, only increment TPS.
                self.steady_state_tps_index = self.steady_state_tps_index + 1
                if self.steady_state_tps_index >= len(self.steady_state_tps_list):
                    # No more TPS values to test.
                    return None
            else:
                # No success yet, so check next type and count combination
                self.initial_instance_count_index = (
                    self.initial_instance_count_index + 1
                )
                if self.initial_instance_count_index >= len(
                    self.initial_instance_count_list
                ):
                    # No more count values to test for this type, so try next type.
                    self.initial_instance_count_index = 0
                    self.instance_type_index = self.instance_type_index + 1
                    if self.instance_type_index >= len(self.instance_type_list):
                        # No more instance types to test
                        return None

        combination = (
            self.host,
            self.region,
            self.endpoint_name,
            self.endpoint_config_name,
            self.model_name,
            self.instance_type_list[self.instance_type_index],
            self.initial_instance_count_list[self.initial_instance_count_index],
            self.ramp_start_tps,
            self.ramp_minutes,
            self.steady_state_tps_list[self.steady_state_tps_index],
            self.steady_state_minutes,
        )
        config = self.plan.configs[combination]
        self.plan.history.append(config)
        return config
