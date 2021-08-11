# Auto Scale Metric

## Background

The `SageMakerVariantInvocationsPerInstance` is the metric AWS recommends for SageMaker autoscaling.

SageMaker autoscaling allows endpoints to run models with a minimum number of instances for cost
efficiency, while still being able to scale up to a maximum number of instances to support peak
traffic.

From
[AWS Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-auto-scaling-add-code-define.html):

```
SageMakerVariantInvocationsPerInstance is the average number of times
per minute that each instance for a variant is invoked. We strongly
recommend using this metric.
```

So this metric determines how many instances are desired based on the current traffic level, and
SageMaker will scale up or down as needed (within bounds of the set min and max).


## Process

The testing process is based on recommendations from
[AWS Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/endpoint-scaling-loadtest.html):

```
Use a load testing tool to generate an increasing number of parallel
requests, and monitor the RPS and model latency in the out put of the
load testing tool.

When the model latency increases or the proportion of successful
transactions decreases, this is the peak RPS that your variant can
handle.

SageMakerVariantInvocationsPerInstance = (MAX_RPS * SAFETY_FACTOR) * 60

Amazon SageMaker recommends that you start testing with a SAFETY_FACTOR
of 0.5.
```

You can run perfsizesagemaker by providing your requirements for peak traffic in TPS, p99 response
time in milliseconds, and acceptable error rate in percentage.

The tool will check if there is a recommended fixed scale setup that works for your requirements.
It determines the maximum number of instances needed to support your stated peak.

The report shows the `SageMakerVariantInvocationsPerInstance` as `invocations_target`.

Optionally, if you want to find an auto scale setup, you will need to define what ramp time (in
minutes) is allowed for traffic to go from 0 TPS to your peak TPS. This process will help you
determine a suitable minimum number instances needed to support your ramp time. You can follow the
steps on this page:

- [How to test for auto scaling settings](auto-scale-testing.md)

