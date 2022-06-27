# How to test for auto scaling settings

## Overview

The perfsizesagemaker tool provides an automated way to determine deployment settings that are
cost effective and meet given performance requirements.

The tool finds these settings:

- `Instance Type`

- `Maximum Instance Count`

- `Scaling Metric` (Report shows it as `invocations_target`)

- `Minimum Instance Count`

If all tests pass, you can use the above settings to deploy your model with either a Fixed Scale
or Auto Scale configuration.

Depending on your model and given requirements, there may be cases where the tool is unable to find
some settings. For example, if type tests and maximum instance count tests pass, you have enough
information to deploy a Fixed Scale configuration. But if there is no solution found for the
minimum instance count tests, then auto scaling does not work with your current requirements.

Below are more details about the testing process.


## Requirements

The minimum instance count specifies how low the endpoint will scale, in times of low traffic.

The tool uses the following requirements when testing for instance type and maximum instance count,
and they will also apply when testing for minimum instance count:

- Peak Traffic (TPS)

- TP99 Response Time (milliseconds)

- Error Rate (%)

In addition, a new requirement is needed:

- Ramp time (minutes) - the duration allowed for traffic to rise from 0 TPS to peak TPS.

So if, for example, your model has these requirements:

- Peak Traffic: 100 TPS

- TP99 Response Time: 200 ms

- Error Rate: 0.01%

- Ramp Time: 60 minutes

then that would mean your model is expecting traffic to rise from 0 TPS to 100 TPS over 60 minutes,
while still meeting the given response time and error rate requirements.

These requirements are specific to your model's use case. To come up with requirements, you might
consider historical metrics and check with clients that will be calling your model.


## Process

The testing tool is now able to test for auto scale settings automatically.

However, you can still review the steps here for reference, or in case you want to run any
additional tests.

1. For finding minimum instance count, start by setting a lower bound at 0 and an upper bound at
   `Maximum Instance Count`.

2. Set the next number to test as `(upper + lower) / 2`, rounded down to an integer. If this number
   was already tested, then stop testing.

3. Deploy your model with the `Instance Type` from the perf test report and set the number of
   instances to the minimum count being tested.

4. Apply auto scale settings, with `Minimum Instance Count` as the current number being tested,
   and get `Maximum Instance Count` and `Scaling Metric` values from the perf test report.

5. Wait for endpoint to complete updating. Use
   [sagemaker-gatling](https://github.com/intuit/sagemaker-gatling)
   to run a load that simulates a ramp from 0 TPS to peak TPS over your given ramp time, and
   continues peak TPS for a steady state duration (for example, 30 minutes).

   IMPORTANT: Your test may be invalid if you skip the redeployment steps above. For example, if you
   just finished running a previous test that sent enough traffic, your endpoint may still be scaled
   out. So running another test immediately on the same endpoint would not be testing ramp from the
   expected minimum count. You would need to wait until the endpoint scaled back down to the minimum
   count, or do the above steps to redeploy to a known starting state.

6. See Gatling report results.

7. Check for success.

   If error rate and TP99 response time look good, then you have found a `Minimum Instance Count`
   setting that supports your requirements. Make a note of current settings. But keep testing to
   see if there is an even lower minimum count possible. Set upper bound to current number and
   repeat from Step 2.

   Else, the current setting did not work, so set lower bound to current number and repeat from
   Step 2.

Once Step 2 detects the next number to test was already tested, go with the most recent successful
`Minimum Instance Count` setting found. Or, if none found, then auto scaling does not work with
your current requirements.


## Tips

- The testing tool is now able to test for auto scale settings automatically, assuming the previous
  test phases for instance type and maximum instance count passed, and a ramp time was given as
  greater than zero.

- There are many models that can support their peak TPS with just 1 or 2 instances of ml.m5.large.
  In this case, you can just deploy with a Fixed Scale configuration and there is no need for auto
  scaling.

- One risk factor could be that you need to spin up a lot of instances. This can happen if you have
  a very high TPS relative to your scaling metric (how much traffic each instance can handle). This
  usually means you will need to allow a longer ramp time (if possible) or start with a higher
  starting number for minimum instance count. Or, you can look at ways to improve the model
  performance itself so it can handle more TPS per instance, so you can get by with fewer instances.

- Another risk factor could be if your expected traffic is very spiky (ramp time shorter than 15
  minutes). This usually means you will need to start with a higher number for minimum instance
  count.  It could even mean that auto scaling is not possible given your requirements.

- If you have questions or feedback, please start a new thread on the
  [perfsizesagemaker Issues](https://github.com/intuit/perfsizesagemaker/issues)
  page at GitHub.

## Sample Reports

(TODO)
