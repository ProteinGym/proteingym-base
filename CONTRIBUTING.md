# Contributing

This file contains documentation about contributing to this project.

## How to release

This section describes how to rlease the package in this project.

### Prerequisites

* Push and merge rights for this repo, 
  [pg2-dataset](https://github.com/ProteinGym2/pg2-dataset),
  also referred to as the *upstream*.
* A UNIX system that has:
  - `git` able to push to upstream

### Release

We use hatch to [version](https://hatch.pypa.io/latest/version/) the project.
Before releasing, you decide which semantic version segement you want to
release, like:

| Segement | New version | 
| -------- | ----------- |
| release  | 1.0.0       |
| major    | 2.0.0       |
| minor    | 1.1.0       |
| patch    | 1.0.1       |
| rc       | 1.0.0rc0    |

> See [docs](https://hatch.pypa.io/latest/version/) for full details.

Then, you run the following

``` bash
$ hatch version release|major|minor|release|patch|rc
$ VERSION=$(hatch version)
$ git checkout -b release/release-v$VERSION
$ git add src/pg2_dataset/__about__.py
$ git commit -m "Bump version to $VERSION"
$ git tag v$VERSION
$ git push --set-upstream origin release/release-v$VERSION
$ git push --tags
```

Create a pull request and wait until it the CI passes. Now make sure you merge
the PR and delete the release branch. The CI will automatically pick the tag up
and release it, wait to appear in PyPI. Only merge if the later happens.
