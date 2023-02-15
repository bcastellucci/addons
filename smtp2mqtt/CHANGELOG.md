## [1.0.2] - 2023-02-15

### Added

- added builder action/workflow to build & publish Docker images automatically (shameless copy from mosquitto addon)

### Changed

- Re-worked message traversal logic, especially attachment logic
- Relegated most of the MIME guesswork to the email library
- Fixed-up encoding issues with attachments
- Other minor refactoring

## [1.0.1] - 2023-01-07

### Added

- added new configuration option - smtp_auth_required (see docs)

### Changed

- Shortened the uuid to 8 characters
- Added armv7 in Dockerfile to match config.yaml and README.md


## [1.0.0] - 2022-09-22

- Initial version
