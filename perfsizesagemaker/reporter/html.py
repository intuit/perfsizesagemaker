from datetime import datetime
from decimal import Decimal
import itertools
import json
import logging.config
import math
from os import path
import pandas as pd
from perfsize.perfsize import Condition, Config, Plan, Result, Run, lt, gte
from perfsize.result.gatling import Metric
from perfsizesagemaker.constants import Parameter, SageMaker
from perfsizesagemaker.cost import CostEstimator
from pprint import pformat, pprint
from typing import Dict, List, Optional, Tuple, Union
import yaml
from yattag import Doc, indent  # type: ignore[attr-defined]

log = logging.getLogger(__name__)


def format(input: str) -> str:
    # Workaround yattag indent returning type Any instead of str
    return str(indent(input))


class HTMLReporter:
    def __init__(
        self,
        inputs: Optional[Dict[str, str]] = None,
        type_plan: Optional[Plan] = None,
        max_count_plan: Optional[Plan] = None,
        min_count_plan: Optional[Plan] = None,
        recommend_type: Optional[Dict[str, str]] = None,
        recommend_max: Optional[Dict[str, str]] = None,
        recommend_min: Optional[Dict[str, str]] = None,
    ):
        self.inputs = inputs
        self.type_plan = type_plan
        self.max_count_plan = max_count_plan
        self.min_count_plan = min_count_plan
        self.recommend_type = recommend_type
        self.recommend_max = recommend_max
        self.recommend_min = recommend_min

        if self.recommend_max:
            explanation = self.recommend_max["max_cost"]
            self.recommend_max["max_cost"] = self.strings_to_html(
                explanation.split("\n")
            )

        if self.inputs and self.recommend_max and self.recommend_min:
            peak_tps = int(self.inputs["peak_tps"])
            max_instance_count = int(self.recommend_max["max_instance_count"])
            self.recommend_min[
                "invocations_target_explanation"
            ] = self.explain_invocations(
                peak_tps, max_instance_count, SageMaker.SAFETY_FACTOR
            )

        # Color Scheme
        self.color = {}
        self.color["pass"] = "e5ffe5"
        self.color["fail"] = "ffeae5"
        self.color["background"] = "f1f6fb"

    def format_unix_time(self, seconds: int) -> str:
        return datetime.utcfromtimestamp(seconds).strftime("%Y-%m-%d %H:%M:%S UTC")

    def explain_invocations(
        self, peak_tps: int, max_instance_count: int, factor: Decimal
    ) -> str:
        return self.strings_to_html(
            (
                f"invocations_target\n"
                f"= int(peak_tps / max_instance_count * 60 * safety_factor)\n"
                f"= int({peak_tps} / {max_instance_count} * 60 * {SageMaker.SAFETY_FACTOR})\n"
                f"= {int(Decimal(peak_tps) / Decimal(max_instance_count) * 60 * SageMaker.SAFETY_FACTOR)}"
            ).split("\n")
        )

    def strings_to_html(self, strings: List[str]) -> str:
        doc, tag, text = Doc().tagtext()
        if not strings:
            print("WARN: Explanation was empty so returning empty string.")
            return ""
        for string in strings:
            with tag("p"):
                text(string)
        return format(doc.getvalue())

    def status_to_html_color(self, status: Optional[bool]) -> str:
        if status == True:
            return f'background-color: {self.color["pass"]}'
        if status == False:
            return f'background-color: {self.color["fail"]}'
        # Everything else (including None) is neutral
        return f'color: {self.color["background"]}; background-color: {self.color["background"]}'

    def highlight_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        # Make a copy so original unchanged
        df_copy = df.copy()
        # Set all to default no color
        df_copy.loc[:, :] = "background-color: "
        # Not sure how to pass in relevant plan, so need to check each one.
        # Find corresponding run and highlight selected metrics.
        plans = [
            plan
            for plan in [self.type_plan, self.max_count_plan, self.min_count_plan]
            if plan is not None
        ]
        for runid, row in df_copy.iterrows():
            for plan in plans:
                for config in plan.history:
                    for run in config.runs:
                        if run.id == runid:
                            for metric in plan.requirements.keys():
                                for result in run.results:
                                    if result.metric == metric:
                                        status = None
                                        if result.successes:
                                            status = True
                                        if result.failures:
                                            status = False
                                        df_copy.loc[
                                            runid, metric
                                        ] = self.status_to_html_color(status)
        return df_copy

    def render_dict(
        self, dictionary: Optional[Dict[str, str]], keys: Optional[List[str]] = None
    ) -> str:
        doc, tag, text = Doc().tagtext()
        if not dictionary:
            with tag("p"):
                text(f"ERROR: Dictionary was empty")
            return format(doc.getvalue())
        subset: Dict[str, str] = {}
        if keys:
            for key in keys:
                subset[key] = dictionary[key]
        else:
            subset = dictionary
        dataFrame = pd.DataFrame.from_dict(subset, orient="index", columns=["value"])
        renderHtmlString = dataFrame.style.set_table_attributes(
            'border="1" class="dataframe table table-hover table-bordered"'
        ).render()
        with tag("p"):
            doc.asis(renderHtmlString)
        return format(doc.getvalue())

    def render_plan(self, plan: Optional[Plan]) -> str:
        doc, tag, text = Doc().tagtext()
        if not plan:
            with tag("p"):
                text(f"ERROR: Test plan was empty")
            return format(doc.getvalue())
        if not plan.history:
            with tag("p"):
                text(f"ERROR: Test plan had no history")
            return format(doc.getvalue())
        type_walk = plan.parameter_lists[Parameter.instance_type]
        count_walk = plan.parameter_lists[Parameter.initial_instance_count]
        tps_walk = plan.parameter_lists[Parameter.steady_state_tps]
        if not type_walk:
            with tag("p"):
                text(f"ERROR: Instance type list was empty")
            return format(doc.getvalue())
        if not count_walk:
            with tag("p"):
                text(f"ERROR: Instance count list was empty")
            return format(doc.getvalue())
        if not tps_walk:
            with tag("p"):
                text(f"ERROR: TPS list was empty")
            return format(doc.getvalue())
        results: Dict[str, Dict[str, Optional[bool]]] = {}
        # Initialize all results to None. Rows are type-count, columns are TPS.
        for typ in type_walk:
            for count in count_walk:
                row_name = f"{typ}-{count}"
                results[row_name] = {}
                for tps in tps_walk:
                    results[row_name][tps] = None
        # Update results based on history.
        for config in plan.history:
            row_name = f"{config.parameters[Parameter.instance_type]}-{config.parameters[Parameter.initial_instance_count]}"
            col_name = config.parameters[Parameter.steady_state_tps]
            if not config.runs:
                with tag("p"):
                    text(f"ERROR: Config {config} was part of history but had no run")
                return format(doc.getvalue())
            # TODO: How to render a config with multiple runs? For now, just use last one.
            results[row_name][col_name] = config.runs[-1].status
        dataFrame = pd.DataFrame.from_dict(results, orient="index", columns=tps_walk)
        renderHtmlString = (
            dataFrame.style.applymap(self.status_to_html_color)
            .set_table_attributes(
                'border="1" class="dataframe table table-hover table-bordered"'
            )
            .render()
        )
        with tag("p"):
            doc.asis(renderHtmlString)
        return format(doc.getvalue())

    def render_runs(self, plan: Optional[Plan]) -> str:
        doc, tag, text = Doc().tagtext()
        if not plan:
            with tag("p"):
                text(f"ERROR: Test plan was empty")
            return format(doc.getvalue())
        if not plan.history:
            with tag("p"):
                text(f"ERROR: Test plan had no history")
            return format(doc.getvalue())
        # Most result values will be Decimal in current implementation.
        # The str are some additional text labels.
        results: Dict[str, Dict[str, Union[Decimal, str]]] = {}
        cols = ["start_time", "end_time"]  # append remaining cols dynamically
        for config in plan.history:
            for run in config.runs:
                row_name = run.id
                results[row_name] = {}
                for result in run.results:
                    col_name = result.metric
                    results[row_name][col_name] = result.value
                    if col_name not in cols:
                        cols.append(col_name)
                # Additional operations on explicit columns expected to exist:
                start_time = results[row_name]["simulation_start"]
                assert isinstance(start_time, Decimal)
                end_time = results[row_name]["simulation_end"]
                assert isinstance(end_time, Decimal)
                results[row_name]["start_time"] = self.format_unix_time(
                    int(start_time / 1000)
                )
                results[row_name]["end_time"] = self.format_unix_time(
                    int(end_time / 1000)
                )
        dataFrame = pd.DataFrame.from_dict(results, orient="index", columns=cols)
        renderHtmlString = (
            dataFrame.style.set_table_attributes(
                'border="1" class="dataframe table table-hover table-bordered"'
            )
            .apply(self.highlight_columns, axis=None)
            .render()
        )
        with tag("p"):
            doc.asis(renderHtmlString)
        return format(doc.getvalue())

    def render(self) -> str:
        doc, tag, text = Doc().tagtext()
        if not self.inputs:
            model = "ERROR"
        else:
            model = self.inputs["model_name"]

        with tag("h1"):
            text(f"{model} - Endpoint Sizing Results")

        with tag("h2"):
            text(f"Recommendation")

        if self.recommend_type and self.recommend_min and self.recommend_max:
            # General success text (either fixed or auto scale)
            with tag("p"):
                text(
                    f"Success! Based on the provided inputs, here are the "
                    f"suggested settings for deploying {model}."
                )
            summary: Dict[str, str] = {}
            summary["instance_type"] = self.recommend_type["instance_type"]
            summary["min_instance_count"] = self.recommend_min["min_instance_count"]
            summary["min_cost"] = self.recommend_min["min_cost"]
            summary["max_instance_count"] = self.recommend_max["max_instance_count"]
            summary["max_cost"] = self.recommend_max["max_cost"]
            summary["invocations_target"] = self.recommend_min["invocations_target"]
            doc.asis(self.render_dict(summary))
            with tag("p"):
                text("For a Fixed Scale configuration, use the max_instance_count.")
            with tag("p"):
                text("For an Auto Scale configuration, use the min_instance_count, ")
                text("max_instance_count, and invocations_target.")

        elif self.recommend_type:
            with tag("p"):
                text(
                    f'Failure! Found instance type {self.recommend_type["instance_type"]} '
                )
                text(f"worked for type tests, but endurance tests failed.")
            with tag("p"):
                text("Please see below for more details.")
        else:
            with tag("p"):
                text("Failure! No solution found given inputs below.")
            with tag("p"):
                text("Please try again with different inputs.")

        with tag("p"):
            text("For more debugging details, go to the Build ")
            text("Artifacts to see detailed reports for each test step.")

        with tag("hr"):
            pass

        with tag("h2"):
            text("Explanation")

        with tag("p"):
            text("The testing process starts by undeploying or deploying the ")
            text("model to get to a known starting state. ")
            text("It will then deploy using instance types specified, one by ")
            text("one, until it finds the first (assuming lowest) instance ")
            text("type that can meet the error rate and response time ")
            text("requirements (see Step 2). ")
            text("Default instance types should cover most cases, but you ")
            text("can override with other types if needed. ")
            text("Default instance count is 1, in order to test how much ")
            text("a single instance can handle. ")
            text("For each instance type, it tests using the TPS rates ")
            text("specified, usually from 1 TPS to 400 TPS, to find how ")
            text("much load a single instance of that type can handle. ")
            text("Default TPS steps should cover most cases, but you ")
            text("can omit or add certain TPS ranges to guide the testing. ")
            text("If an instance type is found, it then extrapolates how ")
            text("many instances of this type would be needed to meet peak ")
            text("TPS based on the load that a single instance was able to ")
            text("handle. ")
            text("To prove that extrapolation, it then runs an endurance ")
            text("test with that instance type and that number of instances, ")
            text("while sending peak TPS (see Step 3). ")
            text("If the endurance test fails, it will try increasing the ")
            text("count and re-testing a few times. ")
            text("The expected result is finding an instance type and count ")
            text("configuration that supports the given requirements. ")
            text("This configuration can then be used either by itself as a ")
            text("Fixed Scale configuration, or as the Maximum Count part of ")
            text("an Auto Scale configuration. ")
            text("For the Minimum Count part of an Auto Scale configuration, ")
            text("check the last section (see Step 4). ")

        with tag("p"):
            text("The perf test needs exclusive access to the model and its ")
            text("endpoint for the entire duration of the test. ")
            text("The perf test will be deploying and undeploying, and ")
            text("sending various traffic patterns. ")
            text("Do not make your own changes or send your own traffic to ")
            text("the endpoint until the test is over. ")
            text("Do not run tests in parallel for the same model endpoint. ")
            text("Any of these activities may interfere with the test run and ")
            text("invalidate results. ")

        with tag("h3"):
            text("1. Inputs")

        with tag("p"):
            text("Here are the performance requirements and other settings ")
            text("used to test the given model. ")

        doc.asis(self.render_dict(self.inputs))

        with tag("h3"):
            text("2. Find Instance Type")

        with tag("p"):
            text("Find the first instance type that works and how much load ")
            text("it can handle.")

        with tag("p"):
            text("Instance Type and Count (left column) vs. TPS (top row):")

        with tag("p"):
            doc.asis(self.render_plan(self.type_plan))

        # Table with runs and Gatling client metrics
        with tag("p"):
            text("Test Configuration (left column) vs. Result Details (top row):")

        with tag("p"):
            doc.asis(self.render_runs(self.type_plan))

        # TODO: Table with SageMaker CloudWatch metrics

        with tag("p"):
            text("Instance Type Result:")

        if self.recommend_type:
            doc.asis(self.render_dict(self.recommend_type))
            with tag("p"):
                text("Results show an instance type meeting SLA rules (for ")
                text("error rate and response time) at a certain TPS level.")
        else:
            with tag("p"):
                text("ERROR: None of the instance types tested were able to ")
                text("meet SLA rules at these TPS levels.")
            with tag("p"):
                text("Please try higher instance types, lower TPS levels, ")
                text("higher error rates, longer response times, revised ")
                text("request payload, and/or revised model code.")
            with tag("p"):
                text("The testing process needs to have an instance type ")
                text("that works in order to proceed. Skipping the ")
                text("remaining steps on this page.")

        with tag("h3"):
            text("3. Find Maximum Count")

        with tag("p"):
            text("Find number of instances needed to support given peak load.")

        if not self.max_count_plan:
            with tag("p"):
                text("This section was skipped either by configuration, ")
                text("or due to above errors.")
        else:
            with tag("p"):
                text("Instance Type: Use the instance type found above.")
            with tag("p"):
                text("Instance Count: The count needed was calculated in the ")
                text("previous step. The endurance test should pass with this ")
                text("count, but in case it fails, the test plan includes ")
                text("some added counts to try.")

            with tag("p"):
                text("Instance Type and Count (left column) vs. TPS (top row):")

            with tag("p"):
                doc.asis(self.render_plan(self.max_count_plan))

            # Table with runs and Gatling client metrics
            with tag("p"):
                text("Test Configuration (left column) vs. Result Details (top row):")

            with tag("p"):
                doc.asis(self.render_runs(self.max_count_plan))

            # TODO: Table with SageMaker CloudWatch metrics

            with tag("p"):
                text("Maximum Count Result:")

            if self.recommend_max:
                doc.asis(self.render_dict(self.recommend_max))
                with tag("p"):
                    text("Results show a working setup to meet the required ")
                    text("TPS, error rate, and response time.")
            else:
                with tag("p"):
                    text("ERROR: Endurance tests failed to meet SLA rules.")
                with tag("p"):
                    text("There can be different reasons for failure. ")
                    text("Sometimes, the cause is an intermittent ")
                    text("environmental issue that can be resolved with a ")
                    text("re-run. Other times, the failure may be consistent ")
                    text("but model specific - it passed the instance type ")
                    text("test, but is not scaling per expected extrapolation.")
                with tag("p"):
                    text("For more debugging details, go to the Build ")
                    text("Artifacts to see detailed reports for each test step.")

        with tag("h3"):
            text("4. Find Minimum Count")

        with tag("p"):
            text("Find number of instances needed to support given ramp time. ")
            text("The endpoint needs to scale up from the minimum number to ")
            text("the maximum number within given ramp time.")

        # if self.recommend_min:
        #     doc.asis(self.render_plan(self.min_count_plan))

        with tag("p"):
            text("This section is a placeholder until automation is ready.")
            # doc.asis(self.render_runs(self.min_count_plan))

        if self.recommend_min:
            doc.asis(self.render_dict(self.recommend_min))

        with tag("p"):
            text("You can also test the minimum instance count by following: ")
            with tag("a", href="TBD"):
                text("How to test for auto scaling settings")
        with tag("p"):
            text("For more context on the autoscale metric, see ")
            with tag("a", href="TBD"):
                text("SageMakerVariantInvocationsPerInstance")
        with tag("p"):
            text("For any questions, please start a new thread on the ")
            with tag("a", href="https://github.com/intuit/perfsizesagemaker/issues"):
                text("perfsizesagemaker Issues")
            text(" page at GitHub.")

        return format(doc.getvalue())
