# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).


## [1.0.2] - 2025-08-16

### Changed
- Reworked UI to make adding template modules more intuitive
- Reworked UI for branch editing

### Fixed
- Resolved build issue with the `quad.legacy` bank option
- Fixed hierarchy issues with isolated skin skeletons


## [1.0.1] - 2025-07-21

### Added
- Introduced a UI for editing the user menu bar
- Added checkbox support in menu actions through toggle callbacks
- Enabled highlight toggling for the logger in the Script Editor (Tools > Logger)

### Changed
- Refactored YAML Dumper/Loader to prevent global overrides
- Cleaned up global preferences reload mechanism


## [1.0.0] - 2025-07-15

### Added

- Initial open source release, based on the internal *Gemini* project.

### Changed
- Major refactor and cleanup to prepare for public use.
- Removed studio-specific code and dependencies.
- Renamed and reorganized modules for clarity and reusability.
