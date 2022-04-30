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

        assert len(plan.parameter_lists[Parameter.variant_name]) == 1
        self.variant_name = plan.parameter_lists[Parameter.variant_name][0]

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
            self.variant_name,
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


# Use binary search to find a suitable scaling_min_instance_count that works,
# given the traffic ramp from ramp_start_tps to steady_state_tps over
# ramp_minutes. Set up plan to have scaling_min_instance_count parameter as
# a list of all possibilities from 1 to scaling_max_instance_count. All other
# parameters would be fixed to single values. Then the actual test walk can
# point to the next step config from the list of possibilities.
class AutoScaleMinFinderStepManager(StepManager):
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

        assert len(plan.parameter_lists[Parameter.variant_name]) == 1
        self.variant_name = plan.parameter_lists[Parameter.variant_name][0]

        assert len(plan.parameter_lists[Parameter.model_name]) == 1
        self.model_name = plan.parameter_lists[Parameter.model_name][0]

        # Should have already identified a working instance_type at this point.
        assert len(plan.parameter_lists[Parameter.instance_type]) == 1
        self.instance_type = plan.parameter_lists[Parameter.instance_type][0]

        # Assert initial_instance_count is not specified. Will force environment
        # manager to use same value as scaling_min_instance_count for each step.
        # And specifying full list here would increase combination space.
        assert Parameter.initial_instance_count not in plan.parameter_lists

        # Assert plan is for auto scale setup.
        assert len(plan.parameter_lists[Parameter.scaling_enabled]) == 1
        self.scaling_enabled = plan.parameter_lists[Parameter.scaling_enabled][0]
        assert self.scaling_enabled == "True"

        # Should have already identified max needed for peak TPS at this point.
        assert len(plan.parameter_lists[Parameter.scaling_max_instance_count]) == 1
        self.scaling_max_instance_count = plan.parameter_lists[
            Parameter.scaling_max_instance_count
        ][0]

        # Possible scaling_min_instance_count is 1 to scaling_max_instance_count.
        assert plan.parameter_lists[Parameter.scaling_min_instance_count] == list(
            map(
                str,
                range(1, int(self.scaling_max_instance_count) + 1),
            )
        )

        assert len(plan.parameter_lists[Parameter.scaling_metric]) == 1
        self.scaling_metric = plan.parameter_lists[Parameter.scaling_metric][0]

        assert len(plan.parameter_lists[Parameter.scaling_target]) == 1
        self.scaling_target = plan.parameter_lists[Parameter.scaling_target][0]

        assert len(plan.parameter_lists[Parameter.ramp_start_tps]) == 1
        self.ramp_start_tps = plan.parameter_lists[Parameter.ramp_start_tps][0]

        assert len(plan.parameter_lists[Parameter.ramp_minutes]) == 1
        self.ramp_minutes = plan.parameter_lists[Parameter.ramp_minutes][0]

        assert len(plan.parameter_lists[Parameter.steady_state_tps]) == 1
        self.steady_state_tps = plan.parameter_lists[Parameter.steady_state_tps][0]

        assert len(plan.parameter_lists[Parameter.steady_state_minutes]) == 1
        self.steady_state_minutes = plan.parameter_lists[
            Parameter.steady_state_minutes
        ][0]

        # Track which scaling_min_instance_count values have been tested so far.
        self.min_count_upper = int(self.scaling_max_instance_count)
        self.min_count_lower = 0
        self.min_count_tested = {self.min_count_lower, self.min_count_upper}
        self.min_count_current = 0

    def next(self) -> Optional[Config]:
        # For calculating what minimum instance count to test next, start with
        # lower bound at 0 and upper bound at max instance count.
        # Calculate next step at half the distance between them (rounded down).
        # If step succeeds, set step as new upper bound. Else, set as new lower.
        # Repeat calculating and testing until next step already tested.

        if not self.plan.history:
            # No tests run yet, so proceed with initial values.
            pass
        else:
            # Check most recent run, assign new bounds based on result.
            previous_config = self.plan.history[-1]
            previous_run = previous_config.runs[-1]
            if previous_run.status:
                self.min_count_upper = self.min_count_current
                self.plan.recommendation = previous_config.parameters
            else:
                self.min_count_lower = self.min_count_current

        # Calculate next step
        self.min_count_current = int((self.min_count_lower + self.min_count_upper) / 2)
        if self.min_count_current in self.min_count_tested:
            # Done testing.
            return None

        # Test next step
        self.min_count_tested.add(self.min_count_current)
        combination = (
            self.host,
            self.region,
            self.endpoint_name,
            self.endpoint_config_name,
            self.variant_name,
            self.model_name,
            self.instance_type,
            # No initial_instance_count set (default to min_count_current)
            self.scaling_enabled,
            str(self.min_count_current),  # scaling_min_instance_count being tested
            self.scaling_max_instance_count,
            self.scaling_metric,
            self.scaling_target,
            self.ramp_start_tps,
            self.ramp_minutes,
            self.steady_state_tps,
            self.steady_state_minutes,
        )
        config = self.plan.configs[combination]
        self.plan.history.append(config)
        return config
