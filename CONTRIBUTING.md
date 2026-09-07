# Contributing to COS Alerter

Thank you for contributing to COS-Alerter. This document aims to help you get started. All contributions must follow the [Ubuntu Code of Conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct).

## Useful links

- [Issues](https://github.com/canonical/cos-alerter/issues)
- [Pull Requests](https://github.com/canonical/cos-alerter/pulls)
- [Ubuntu Code of Conduct](https://ubuntu.com/community/docs/ethos/code-of-conduct)

## Reporting bugs, proposing features

If you find a bug or want to propose a new feature, consider opening an issue for it.

1. Go to our [issue tracker](https://github.com/canonical/cos-alerter/issues).
2. Check if it was already reported by someone else. If yes, feel free to give it a thumbs up to help prioritise work.
3. If you are reporting a security issue, follow the instructions in the [SECURITY.md](./SECURITY.md).
4. If it is a bug, make sure you provide sufficient context to help triage and the person working on the issue:
    - What did you try to achieve? What is the expected and the actual outcome? Does it have a workaround?
    - Describe your environment (OS, install method, exact version of COS Alerter, etc.).
    - Include reproducibility steps when possible.
    - Include any relevant logs. (Make sure to remove sensitive information.)
    - Include anything else you think can help resolve the issue.
5. If the issue is about a new feature, provide sufficient context and describe your proposal as clearly as you can:
    - What is the current state of COS Alerter relevant for the proposal?
    - What is the targeted use case of the proposed feature?
    - What is the benefit of the proposal?

## Working on the code, contributing patches

### Find something to work on

To help new contributors get started, some issues are tagged as [good first issue](https://github.com/canonical/cos-alerter/issues?q=is%3Aissue%20state%3Aopen%20label%3A%22good%20first%20issue%22). These are a good starting point to get familiar with the project.

If you want to comment on the issue that you are working on it, please also provide a reasonable time estimate for when you will be ready with your work.

If there is no open issue but you have a great idea, consider opening an issue about it before investing significant work.

### Getting the code

### Setup your development environment

1. Create a virtual environment: `python3 -m venv venv`
2. Activate it: `source venv/bin/activate`
3. Install COS Alerter in editable mode: `pip install -e ./`

### Run COS Alerter

When your virtual environment is activated, you can run COS Alerter directly from the command line.

```
cos-alerter
```

Look at the full options with `cos-alerter --help`.

### Run With Docker (when relevant)

Prepare the image:
```shell
rockcraft pack
skopeo --insecure-policy copy oci-archive:cos-alerter_0.2.0_amd64.rock docker-daemon:cos-alerter:0.2.0
```

Run:
```shell
cp config-defaults.yaml cos-alerter.yaml
# Update cos-alerter.yaml with appropriate values
docker run -p 8080:8080 --rm --mount type=bind,source="$(pwd)"/cos-alerter.yaml,target=/etc/cos-alerter.yaml,readonly -it cos-alerter:0.2.0
```

### Run the tests

Install `tox` if not yet installed:

```pip install tox```

Run all the tests at once:

```tox```

Run `tox list` to see all the different targets.

### Submitting your work

- Each commit must be [digitally signed and verified](https://docs.github.com/en/authentication/managing-commit-signature-verification/signing-commits). 
- Commit messages must follow [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
- Don't forget to update the [CHANGELOG.md](./CHANGELOG.md) with your relevant changes.
- Push your changes and [open a PR](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/creating-a-pull-request-from-a-fork).
- PRs go through a review process and must pass all checks. Please pay attention to reviewer comments and communicate your availability when necessary.

