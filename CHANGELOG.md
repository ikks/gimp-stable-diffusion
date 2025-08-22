# Changelog

All notable changes to this project will be documented in this file.

This plugin has a version for Gimp2.10.X series and Gimp3 series.
Gimp2 series will not receive more updates, unless a PR is made
and approved.

## [3.2] - Metadata information

### Added

- Metadata is stored to improve reproducibility and transparency
- Debugging can be activated from UI

### Changed

- Python3.8 support is back
- Visible references from StableHorde to AIHorde
- Longer time between checking to consume less kudos
- When an image is censored a message is shown instead of
  showing an image with this same information 

## [3.1] - Improved UI messages

### Added

- UI Messages have improved information
- When the time taking to generate is too long, a fallback is presented
 in a text layer to be able to use the browser to download the image.
- Improved progressbar ticks.
- Warnings avoided when possible with default parameters

### Fixed

- GeglBuffers leaked messages
- Better management on network errors to avoid nested exception

## [3.0.2] - Hotfix release

### Fixed

- Shebang problem fixed
 
## [3.0.1] - Hotfix release

### Fixed

- When there is a network issue, an exception was raised after
  image creation checking for a new plugin release.

## [3.0] - Model updates

### Added

- Now models are updated with the latest ones published by StableHorde
  featuring the most used during the month, for TXT2IMG, IMG2IMG and
  inpainting
- Versioning uses again semver as the initial author started.

## [8] - i18n support

### Added

* Spanish support and infrastructure for translating to other
languages.

## [7] - Gimp3 series release - 2025-07-23

### Added

- Image Creation from Prompt, no need to have an initial image (T2I).
- Create an image from a prompt using an style image (I2I).
- Adjust Image Region (Inpaint).
- For each option, the selections are saved automatically.

## [141] - Gimp2 series - 2023-12-15

- Image Creation from Prompt (T2I).
- Create an image from a prompt using an style image (I2I).
- Adjust Image Region (Inpaint).
- For each option, the selections are saved automatically.
- Added reference to Gimp3 plugin
