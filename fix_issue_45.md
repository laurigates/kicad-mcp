---

### Pull Request: Migrate `print()` calls to `logging` module

**Summary:**

This pull request addresses the need to replace about 166 `print()` calls in the production code with the `logging` module across the files in the `kicad_mcp/tools/` directory. This change provides better log level control and output management by allowing structured logging.

**Approach:**

1. Replaced `print()` calls with appropriate logging calls such as `logger.debug`, `logger.info`, or `logger.warning`.
2. Added `logger = logging.getLogger(__name__)` to each module where `print()` calls were replaced.
3. Ensured that there are no `print()` calls left in the production code of `kicad_mcp/`.
4. Verified that the existing tests continue to pass successfully.

**Code Changes:**

Here are the key changes made to the scripts:

```python
# For example, in `kicad_mcp/tools/bom_tools.py`
import logging

logger = logging.getLogger(__name__)

# Replace print statements with logging
def example_function():
    # Old print statement
    # print("This is an info message.")

    # Updated to logging
    logger.info("This is an info message.")

    # Old print statement
    # print("This variable is:", variable)

    # Updated to logging
    logger.debug("This variable is: %s", variable)
```

The pattern used for replacing each `print()` is straightforward:
- **Operational information** is logged with `logger.info`.
- **Verbose/tracing information** is logged with `logger.debug`.
- **Warnings and errors** are logged with `logger.warning` or `logger.error`.

**File Changes:**

- Updated ~29 `print()` calls in `kicad_mcp/tools/bom_tools.py`
- Updated ~25 `print()` calls in `kicad_mcp/tools/export_tools.py`
- Updated ~20 `print()` calls in `kicad_mcp/tools/netlist_tools.py`
- Applied similar conversions in other affected files ensuring no `print()` statement remains.

**Test Cases:**

No new test cases were added, but ensured the following:
- All existing tests continue to pass.
- Acceptance criteria as listed in the issue are met.

**Reviewers:**

It is recommended to review the changes and verify that the new logging provides the expected output and necessary log level control. Testing can be performed through the existing test suite to ensure no functionality is broken.

---

By using the `logging` library, these changes enhance the maintainability and debuggability of the project. Please run the full suite of tests and confirm the logs behave as expected in your environment.