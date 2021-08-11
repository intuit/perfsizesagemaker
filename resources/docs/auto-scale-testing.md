# How to test for auto scaling settings

## Overview

The perfsizesagemaker tool provides an automated way to determine deployment settings that are
cost effective and meet given performance requirements.

Currently, the tool finds:

- `Instance Type`

- `Maximum Instance Count`

- `Scaling Metric` (Report shows it as `invocations_target`)

But the `Minimum Instance Count` is not yet covered.

With the current perf test report, you have enough information to deploy with a Fixed Scale
configuration.  But to deploy with an Auto Scale configuration, you also need to determine the
minimum number.

There are future plans to automate finding that as well, but for now, please see steps below.

## Requirements

The minimum instance count specifies how low the endpoint will scale in times of low traffic.

These requirements from the automated test report can be reused here:

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

Follow these steps to determine if auto scaling is possible, and if so, what setting to use for
minimum instance count.

1. Try a minimum count = 1 instance as the lowest starting point, or if needing to cover multiple
   availability zones, can start with minimum count = 2.

2. Deploy your model with auto scale settings. Use the `Instance Type`, `Maximum Instance Count`,
   and `Scaling Metric` from the perf test report. But set `Minimum Instance Count` to the current
   number you are testing.

3. After endpoint is finished updating, use 
   [sagemaker-gatling](https://github.com/intuit/sagemaker-gatling)
   to run a load that simulates a ramp from 0 TPS to peak TPS over your given ramp time, and
   continues peak TPS for a steady state duration (for example, 30 minutes).

4. See Gatling report results.

5. Check for success.

If error rate and TP99 response time look good, then you have found a `Minimum Instance Count`
setting that supports your requirements (there may be lower numbers you can further test if you
skipped over some).

Else, the current setting did not work, so bump up minimum count, and repeat with a new deployment
in Step 2.

Once minimum count gets bumped up all the way to maximum count, then auto scaling is not possible
with your current requirements.

## Tips

- Remember you can start with the automated performance test to get most of the settings needed.
  The manual retry steps on this page are only for finding the minimum instance count.

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
