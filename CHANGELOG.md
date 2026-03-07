# Changelog

## [0.2.0](https://github.com/laurigates/kicad-mcp/compare/v0.1.0...v0.2.0) (2025-08-05)


### Features

* complete HTTP testing framework with MCP protocol integration ([#36](https://github.com/laurigates/kicad-mcp/issues/36)) ([29cf562](https://github.com/laurigates/kicad-mcp/commit/29cf562e0351f5aea0459226d845f4fc9ff6273b))
* enhance component boundary validation and intelligent wiring system ([#34](https://github.com/laurigates/kicad-mcp/issues/34)) ([b4a44ea](https://github.com/laurigates/kicad-mcp/commit/b4a44eaf99734c7464ae4d8df6e1a059d317e0b2))


### Bug Fixes

* **security:** resolve B607 subprocess security issues in DRC CLI ([#37](https://github.com/laurigates/kicad-mcp/issues/37)) ([62e1218](https://github.com/laurigates/kicad-mcp/commit/62e1218473e34a5a7d1004bf0b8b8e038ae4c2fb))

## 0.1.0 (2025-07-30)


### Features

* Add comprehensive test suite and KiCad documentation ([b02f26e](https://github.com/laurigates/kicad-mcp/commit/b02f26e9dc0d5930d07bead584714caf75742fee))
* Add modern Python packaging and CI workflow ([c7665e2](https://github.com/laurigates/kicad-mcp/commit/c7665e24b02d0efc76ef4b52ef7c28870d3630a3))
* centralize KiCad file format version management ([#33](https://github.com/laurigates/kicad-mcp/issues/33)) ([7270a2b](https://github.com/laurigates/kicad-mcp/commit/7270a2b2f9b0a882248a9f1a22ba89ad2cf40468))
* Fix tools, improve stability, and update docs ([5b9d237](https://github.com/laurigates/kicad-mcp/commit/5b9d237d7d740e9ae433178735bcd795ce0da83d))
* implement comprehensive boundary validation system for component positioning ([#31](https://github.com/laurigates/kicad-mcp/issues/31)) ([2f2f405](https://github.com/laurigates/kicad-mcp/commit/2f2f4050df3efb420893358bbfdcd9263f46579d))
* implement comprehensive KiCad component layout and pin-level connectivity system ([#13](https://github.com/laurigates/kicad-mcp/issues/13)) ([aca66f7](https://github.com/laurigates/kicad-mcp/commit/aca66f7f54c94d3d9c2a37359613a41905a84031))
* implement comprehensive KiCad component layout and pin-level connectivity system ([#8](https://github.com/laurigates/kicad-mcp/issues/8)) ([2e9e07b](https://github.com/laurigates/kicad-mcp/commit/2e9e07b64ba742e4571da5527c16c9f76f1b8417))
* implement comprehensive security improvements and code quality enhancements ([#24](https://github.com/laurigates/kicad-mcp/issues/24)) ([d5639ef](https://github.com/laurigates/kicad-mcp/commit/d5639eff751aa32d58eba188f476dfcf4dde9c01))
* implement visual schematic rendering system ([#7](https://github.com/laurigates/kicad-mcp/issues/7)) ([0394a4f](https://github.com/laurigates/kicad-mcp/commit/0394a4f94f660eafd8e712120f6c7d37b648b0f5))


### Bug Fixes

* add missing fastmcp dependency to pyproject.toml ([#12](https://github.com/laurigates/kicad-mcp/issues/12)) ([92f17b7](https://github.com/laurigates/kicad-mcp/commit/92f17b798f9570d4f53ab4b7c5ac3872b22292ae))
* cherry-pick test compatibility and CI improvements ([#23](https://github.com/laurigates/kicad-mcp/issues/23)) ([bd85197](https://github.com/laurigates/kicad-mcp/commit/bd851972a8ae441ad4e8a9584225ce6b6fe94d5f))
* **ci:** dependency installation syntax for UV dependency groups ([#11](https://github.com/laurigates/kicad-mcp/issues/11)) ([b729b66](https://github.com/laurigates/kicad-mcp/commit/b729b663501011cccd843ea0398b6e0f0a0055fe))
* **ci:** workflow and config ([#9](https://github.com/laurigates/kicad-mcp/issues/9)) ([4c86551](https://github.com/laurigates/kicad-mcp/commit/4c86551af6075ec34a7ffab768bf908a9dd7a84d))
* Generate proper KiCad S-expression format instead of JSON ([bee1948](https://github.com/laurigates/kicad-mcp/commit/bee1948981eb4829887584c599be2cdd5ff326b6))
* resolve critical circuit generation and validation issues ([8678f30](https://github.com/laurigates/kicad-mcp/commit/8678f30fbf395f7f56d964246ce54c95153fe933))
* resolve issue [#5](https://github.com/laurigates/kicad-mcp/issues/5) - implement missing server lifecycle functions ([#6](https://github.com/laurigates/kicad-mcp/issues/6)) ([21411a2](https://github.com/laurigates/kicad-mcp/commit/21411a2392ae4c7038fc5c14b9605affdf84e852))
* resolve merge conflict markers and update to FastMCP 2.0 imports ([#15](https://github.com/laurigates/kicad-mcp/issues/15)) ([2787ca9](https://github.com/laurigates/kicad-mcp/commit/2787ca9ffd31ecaee62f1c463063a40a8a5c4334))
* **server:** startup errors ([#17](https://github.com/laurigates/kicad-mcp/issues/17)) ([251d0ba](https://github.com/laurigates/kicad-mcp/commit/251d0baa11895c29e42b5ddd1a3d5623a5c9f54e))
* **test:** update circuit_tools tests for FastMCP 2.0 compatibility ([#21](https://github.com/laurigates/kicad-mcp/issues/21)) ([8f9bbda](https://github.com/laurigates/kicad-mcp/commit/8f9bbda5324d1e0a4ff04c510477175c19a634d4))


### Documentation

* Add docstrings component_layout e component_utils ([#32](https://github.com/laurigates/kicad-mcp/issues/32)) ([1bc451c](https://github.com/laurigates/kicad-mcp/commit/1bc451c9a322ee2fba1988681715b0efeace51ab))
* Add Google-style docstrings to analysis_tools.py ([#26](https://github.com/laurigates/kicad-mcp/issues/26)) ([13bc192](https://github.com/laurigates/kicad-mcp/commit/13bc1923cf455adefddee07b5b33be0e56542e28))
* Update to use uv pip with pyproject.toml instead of requirements.txt ([8cfbd9a](https://github.com/laurigates/kicad-mcp/commit/8cfbd9a61dca9900c817b17f356536c3ab684c0e))
