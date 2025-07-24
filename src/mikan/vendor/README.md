# Third-party dependencies and custom patches

This folder contains external Python libraries and scripts bundled directly with the project to ensure compatibility and ease of use in constrained environments like Maya.


## Bundled libraries

| Library       | Notes                                                          | License              |
|---------------|----------------------------------------------------------------|----------------------|
| **geomdl**    | Copied and slightly modified to fit project needs.             | MIT                  |
| **pyparsing** | Included as-is for parsing utilities.                          | MIT                  |
| **yamllint**  | Included as-is for YAML linting support.                       | GPL version 3        |
| **unidecode** | Adapted with minor modifications to meet project requirements. | GPLv2+               |
| **cmdx**      | Includes local hotfixes pending upstream submission.           | BSD-2-Clause license |
| **Qt.py**     | Included as-is for PySide compatibility                        | MIT                  |


## Important notes

- Please treat these dependencies as read-only unless you plan to contribute fixes back upstream.
- This approach avoids the complexity of installing these packages in environments like Maya where pip support can be limited.
- Licenses for all bundled packages and scripts are included to comply with their respective terms.

If you contribute or update any of these packages, please document your changes clearly and consider submitting patches upstream.


## cmdx — with local monkey patches

We use a custom version of `cmdx` from the original repo by mottosso, bundled in `vendor/`.


There are **two levels of customization** applied:

1. **Direct edits to the original `cmdx.py`** — small fixes made inline.
2. **Runtime monkey patch (`mikan/maya/cmdx.py`)** — additional behaviors layered on top of the base implementation, loaded at runtime.

This approach lets us isolate core library tweaks while keeping higher-level project logic separate.

> ⚠️ The patched version of `cmdx` is not compatible with the upstream library out-of-the-box. Replacing it may break the tool.

See: [`mikan/maya/cmdx.py`](../src/mikan/maya/cmdx.py) for details.

Source: https://github.com/mottosso/cmdx (MIT)


## Credits and Third-Party Code Reuse

Several modules in this project are based on or inspired by open-source code. In all cases, the original authors are credited in the file headers, and the licenses are preserved.

### mikan/core/expression.py

This file is an adapted version of the `dge.py` module from Chad Vernon's [cmt rigging tools](https://github.com/chadmv/cmt).

Only a subset of the original code was used, focused on the DGE expression generation utilities. The code has been rewritten and reorganized to fit this project’s needs.

Original source:
- Repository: https://github.com/chadmv/cmt
- File: `cmt/dge.py`
- License: MIT (included)

Credits to Chad Vernon for the original implementation.
