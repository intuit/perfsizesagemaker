![perfsizesagemaker logo](.github/assets/images/perfsizesagemaker-logo.png)

# perfsizesagemaker

[![Python Publish](https://github.com/intuit/perfsizesagemaker/actions/workflows/python-publish.yml/badge.svg)](https://github.com/intuit/perfsizesagemaker/actions/workflows/python-publish.yml)

`perfsizesagemaker` is a tool that automates performance testing to determine the right size of
infrastructure for AWS SageMaker endpoints. Given requirements for latency and error rate, the tool
tries various instance type and count configurations to see which ones can meet the requirements,
and then provides a recommendation and detailed report.

- To determine what configuration to test next, a
[step manager](perfsizesagemaker/step/sagemaker.py)
follows prescribed logic based on results collected so far.

- To update the environment, an
[environment manager](perfsizesagemaker/environment/sagemaker.py)
uses
[AWS SDK for Python (Boto3)](https://aws.amazon.com/sdk-for-python/)
to interact with the designated AWS account for each configuration.

- To send traffic, a
[load manager](perfsizesagemaker/load/sagemaker.py)
uses
[sagemaker-gatling](https://github.com/intuit/sagemaker-gatling)
to call the SageMaker endpoint with the desired traffic level per configuration.

- `perfsizesagemaker` can also serve as a reference implementation for how to use the
[perfsize](https://github.com/intuit/perfsize)
library, which has some interfaces and components that can be reused in other implementations for
testing other types of infrastructure.

## Installation

`perfsizesagemaker` is published to PyPI

Install using `pip` (or your preferred dependency manager and virtual environment):

```bash
pip install perfsizesagemaker
```

## Usage

### Prerequisites

- Python 3.8+

### Demo

You can run perfsizesagemaker on any SageMaker endpoint in your AWS account.

But the steps in this demo will use
[model-simulator](https://github.com/intuit/model-simulator)
as an example model for setting up a SageMaker endpoint to test.

Follow the steps in the
[model-simulator README](https://github.com/intuit/model-simulator/blob/main/README.md)
to set up the model in your account and check the SageMaker endpoint is working as expected.

Follow the steps in the
[sagemaker-gatling README](https://github.com/intuit/sagemaker-gatling)
to build the `sagemaker-gatling-1.0-SNAPSHOT-fatjar.jar` and save a copy here as
`sagemaker-gatling.jar`. Or, you can also download from the
[sagemaker-gatling package](https://github.com/intuit/sagemaker-gatling/packages/913839)
page.

You can supply AWS credentials as environment variables to access your account:
```
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

Run `perfsizesagemaker/main.py` with these options:
```
poetry shell

python perfsizesagemaker/main.py \
--host runtime.sagemaker.us-west-2.amazonaws.com \
--region us-west-2 \
--endpoint_name LEARNING-model-simulator-1 \
--endpoint_config_name LEARNING-model-simulator-1-0 \
--model_name model-simulator \
--scenario_requests '[{"path":"samples/model-simulator/sample.input.json","weight":100}]' \
--peak_tps 5 \
--latency_success_p99 500 \
--percent_fail 0.1 \
--type_walk ml.m5.large,ml.m5.xlarge \
--count_walk 1 \
--tps_walk 1,10,100 \
--duration_minutes 1 \
--endurance_ramp_start_tps 0 \
--endurance_ramp_minutes 0 \
--endurance_steady_state_minutes 1 \
--endurance_retries 3 \
--perfsize_results_dir perfsize-results-dir
```

### Sample Jenkinsfile

Another usage option is to use Jenkins to host a job for running perf tests.

In your AWS Account, create a role with permission to deploy, undeploy, and send traffic.
- AWS Console > IAM Management Console > Roles > Create role
- Choose a use case > `SageMaker`. Next.
- Attached permissions policies shows `AmazonSageMakerFullAccess`. Next.
- Role name: `perfsizesagemaker_role`

If other roles (like the role your Jenkins server is using) will need to assume the above role, you
can allow that by:
- IAM > Roles > perfsizesagemaker_role > Trust relationships > Edit trust relationship
- Add an entry for the Jenkins role (where test job is running) to assume the
  perfsizesagemaker_role (where endpoint is running):
```
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::222222222222:role/your-jenkins-role-name-here"
      },
      "Action": "sts:AssumeRole"
    },
```

See [JenkinsfilePerfTest](JenkinsfilePerfTest) as an example.

### Tests

See tests folder for more examples.


## Development

Clone repository:

```
git clone https://github.com/intuit/perfsizesagemaker.git
cd perfsizesagemaker
```

Install `poetry` for dependency management and packaging:
```
https://python-poetry.org/docs/
```

Set up your virtual environment (with package versions from `poetry.lock` file):
```
poetry install
```

Start a shell for your virtual environment for running additional commands that need access to the
installed packages:
```
poetry shell
python anything.py
```

Other commands from the Makefile:
- `make format`: format code with [black](https://github.com/psf/black)
- `make test`: run all tests
- `make build`: create artifacts
- `make publish`: push artifacts to Artifactory

See packages installed:
```
poetry show --tree
```

See info about environments:
```
poetry env info
poetry env list
```

### Integration with your IDE

Optional. For integration with your IDE, you can run `poetry env info` to get the Virtualenv path,
like `/Users/your-name-here/Library/Caches/pypoetry/virtualenvs/perfsizesagemaker-VvRdEPIE-py3.9`, and point your IDE
to the `bin/python` there.

In IntelliJ:
- Create a new Python SDK option under
  `File > Project Structure > Platform Settings > SDKs > Add new Python SDK > Virtualenv Environment > Existing environment > Interpreter`
  and specify the path above including `bin/python`.
- Update `Project Settings > Project SDK` and `Project Settings > Modules > Module SDK` to point to
  the SDK you just created.


## Publishing a Release️

Make sure you are doing this from a clean working directory.

Possible release types are:
- `patch`
- `minor`
- `major`
- `prepatch`
- `preminor`
- `premajor`
- `prerelease`

```bash
VERSION_BUMP_MSG=$(poetry version --no-ansi <release>)
NEW_VERSION=$(poetry version --no-ansi | cut -d ' ' -f2)
git commit -am "${VERSION_BUMP_MSG}"
git tag "v${NEW_VERSION}"
git push && git push --tags
```

Once pushed, Jenkins will automatically publish the artifact to Artifactory.


## Contributing

Feel free to open an
[issue](https://github.com/intuit/perfsizesagemaker/issues)
or
[pull request](https://github.com/intuit/perfsizesagemaker/pulls)!

For major changes, please open an issue first to discuss what you would like to change.

Make sure to read our [code of conduct](CODE_OF_CONDUCT.md).


## License

This project is licensed under the terms of the [Apache License 2.0](LICENSE).
