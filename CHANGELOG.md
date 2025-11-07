# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.4] - 2025-11-07

### Added

- Middle-click drag & drop support in the template tree view
- New IDs for `core.joints` and derivatives when `do_ctrl` is disabled
- In-view messages for posing actions and skin layer switching
- Improved handling of `shape.channel` animation data in mod shapes

### Changed

- Reworked Maya DAG menu injection
- Added tooltips to template module options for better clarity
- Removed legacy twist from `rig.spline`
- Reworked `mod.shape.channel`
- Adjusted minor UI components for PySide6 and Maya 2026 compatibility
- Scaling enabled on clavicle root joints in common limbs
- Refactored blendshape delta reading and reference shape handling
- Fixed stretch IK graph handling in Maya

### Fixed

- Resolved issue with merge down option in build
- PySide6 compatibility fixes in various UI components
- Fixed `util.camera` template build in Tangerine

## [1.0.3] - 2025-09-22

### Added

- Snippets to launch Tangerine from the menu
- Additional tooltips in menus

### Changed

- Automatic renaming of shape hierarchies in the blueprint
- Added geometry and deformer IDs in the mod inspector
- Added `#/ignore` command in the mod parser
- Fixed vis group handling in the `neck.legacy` module
- Allow adding nodes after j/sk nodes in all modules based on `core.joints`

### Fixed

- Preserve shape assignments when modifying branches
- Fixed retrieval of plug IDs for matrices in Maya
- Fixed an issue with inverse scale in the mirror joints function
- Fixed branch display in edit mode in the outliner
- Fixed crash in Tangerine due to improperly handled imports

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
