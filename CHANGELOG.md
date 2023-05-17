# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [UNRELEASED]

## [0.10.0] - 2023-05-17

### Authors

- Faiyaz Hasan <faiyaz@agnostiq.ai>
- Co-authored-by: pre-commit-ci[bot] <66853113+pre-commit-ci[bot]@users.noreply.github.com>


### Added

- GCP Batch Readme banner.

### Changed

- precommit yml version updates.

## [0.9.0] - 2023-05-16

### Authors

- Venkat Bala <venkat@agnostiq.ai>
- Faiyaz Hasan <faiyaz@agnostiq.ai>
- Venkat Bala <15014089+venkatBala@users.noreply.github.com>
- Alejandro Esquivel <ae@alejandro.ltd>
- Venkat Bala <balavk89@gmail.com>


### Changed

- Updated tests workflow to force push to main

## [0.8.0] - 2023-05-16

### Authors

- Venkat Bala <venkat@agnostiq.ai>
- Faiyaz Hasan <faiyaz@agnostiq.ai>
- Venkat Bala <15014089+venkatBala@users.noreply.github.com>
- Alejandro Esquivel <ae@alejandro.ltd>
- Venkat Bala <balavk89@gmail.com>


### Changed

- Removed mounting storage bucket into the container.
- Revert to downloading the objects using google cloud sdk.
- Fixes to Terraform script and outputs.
- Fixed bugs in exec script.
- Updated cache_dir to have a default value.

## [0.7.1] - 2023-03-10

### Authors

- Venkat Bala <venkat@agnostiq.ai>
- Faiyaz Hasan <faiyaz@agnostiq.ai>
- Venkat Bala <15014089+venkatBala@users.noreply.github.com>
- Alejandro Esquivel <ae@alejandro.ltd>
- Venkat Bala <balavk89@gmail.com>


### Fixed

- Fixed parsing of rc suffix flag in changelog action

## [0.7.0-rc.0] - 2023-03-10

### Authors

- Venkat Bala <venkat@agnostiq.ai>
- Faiyaz Hasan <faiyaz@agnostiq.ai>
- Venkat Bala <15014089+venkatBala@users.noreply.github.com>
- Alejandro Esquivel <ae@alejandro.ltd>
- Venkat Bala <balavk89@gmail.com>


### Added

- Added modified describe & changelog reusable actions

### Changed

- Updated changelog to use reusable actions
- Fixed changelog workflow by adding npm modules in build

## [0.5.0] - 2023-03-07

### Added

- Base implementation of the `GCPBatchExecutor`
- Adding unit tests for the executor and its container entrypoint

## [0.4.0] - 2023-03-06

### Changed

- Changelog workflow (to not use reusable action and postpone that for later).

## [0.3.0-rc.0] - 2023-03-01

### Authors



### Added

- Dummy method and test

## [0.2.0-rc.0] - 2023-03-01

### Authors



### Added

- Mock tests x 2

### Operations

- Updating changelog workflow to reuse actions.

## [0.1.0] - 2023-03-01


### Added

- Initial repo setup files.
- Preliminary GitHub workflows.
- GCP Batch README.
