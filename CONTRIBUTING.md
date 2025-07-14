# Contributing

This file contains documentation about contributing to this project.

## How to release

This section describes how to release the package in this project.

### Prerequisites

* Push and merge rights for this repo, 
  [pg2-dataset](https://github.com/ProteinGym2/pg2-dataset),
  also referred to as the *upstream*.
* A UNIX system that has:
  - `git` able to push to upstream

### Release

We use hatch to [version](https://hatch.pypa.io/latest/version/) the project.
Before releasing, you decide which semantic version segment you want to
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
$ hatch version release|major|minor|patch|rc
$ VERSION=$(hatch version)
$ git checkout -b release/v$VERSION
$ git add src/pg2_dataset/__about__.py
$ git commit -m "Release v$VERSION"
$ git tag v$VERSION
$ git push --set-upstream origin release/v$VERSION
$ git push --tags
```

Create a pull request and wait until the CI passes. The CI will automatically
pick the tag up to create a release. When the release appears on Github close
the PR.
