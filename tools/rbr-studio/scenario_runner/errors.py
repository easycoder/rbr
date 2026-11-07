"""The one exception type a caller should catch."""


class ScenarioError(Exception):
    """A scenario or configuration problem, not a failure inside the page."""
