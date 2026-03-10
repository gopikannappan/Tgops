"""Custom exception hierarchy for TGOps."""


class TGOpsError(Exception):
    """Base exception for all TGOps errors."""
    ...


class AuthError(TGOpsError):
    """Raised when authentication fails or session is invalid."""
    ...


class FloodWaitError(TGOpsError):
    """Raised when Telegram imposes a flood wait."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"FloodWait: retry after {retry_after}s")


class OwnershipTransferError(TGOpsError):
    """Raised when ownership transfer fails."""
    ...


class GroupNotFoundError(TGOpsError):
    """Raised when a group cannot be found."""
    ...


class MemberNotFoundError(TGOpsError):
    """Raised when a member cannot be found in a group."""
    ...


class MemberIsOwnerError(TGOpsError):
    """Raised when trying to remove/ban a group owner."""
    ...


class InsufficientPrivilegesError(TGOpsError):
    """Raised when the bot/user lacks required privileges."""
    ...


class MigrationStepError(TGOpsError):
    """Raised when a specific migration step fails."""

    def __init__(self, msg: str, step: str, job_id: str, recoverable: bool = True):
        self.step = step
        self.job_id = job_id
        self.recoverable = recoverable
        super().__init__(msg)
