# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.9.0] - 2024-05-30

- Adding PagerDuty native support (#76).


## [0.8.0] - 2024-03-07

- Fixes container silently running by exiting with non-zero status when configuration file is missing. (#70).

## [0.7.0] - 2024-02-26

- Client state is now retained on a graceful shutdown (#66).

## [0.6.0] - 2023-11-30

- Added badges to README.md (#62).
- Config now accommodates client ID, key, and name, allowing users to specify individual client details (#63).
- Added client authentication using SHA512-hashed keys for enhanced security (#63).


## [0.5.0] - 2023-10-26

- Added usage instructions to the readme (#51).
- Added snapcraft build recipes and automation. (#52)
- Added the ability to set the listen address and port for the web server. (#55)

## [0.4.0] - 2023-05-31

### Added

- Simple UI added to show the state of clients (#47).
- Defaults for config file values (#44).

## [0.3.0] - 2023-04-28

### Added

- `--config` argument for specifying the location of the config file (#36).
- OpenMetrics endpoint (#39).

### Changed

- `Dockerfile` was replaced with `rockcraft.yaml` (#35).

## [0.2.0] - 2023-04-13

### Added

- Initial Release.

## [0.1.0] - 2023-04-13 [YANKED]

### Added

- Improperly uploaded initial release.
