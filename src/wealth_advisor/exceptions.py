class WealthAdvisorError(Exception):
    """Base exception for the wealth advisor system."""


class ToolError(WealthAdvisorError):
    """Raised when a tool layer fails."""


class ApprovalRequired(WealthAdvisorError):
    """Raised when a recommendation is waiting for human validation."""
