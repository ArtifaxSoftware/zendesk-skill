"""Tests for the cross-platform owner-only permission helpers."""

from zendesk_skill.utils.file_perms import is_owner_restricted, restrict_to_owner


def test_restrict_to_owner_makes_file_owner_only(tmp_path):
    """After restrict_to_owner, is_owner_restricted should be True."""
    p = tmp_path / "secret.txt"
    p.write_text("secret")
    restrict_to_owner(p)
    assert is_owner_restricted(p)


def test_is_owner_restricted_missing_file(tmp_path):
    """Missing files are never reported as restricted."""
    assert not is_owner_restricted(tmp_path / "no_such_file")


def test_restrict_to_owner_missing_file_does_not_raise(tmp_path):
    """Calling restrict_to_owner on a missing path should never raise."""
    restrict_to_owner(tmp_path / "no_such_file")  # no assertion — must not raise


def test_default_world_readable_file_is_not_owner_only(tmp_path):
    """Sanity: a file created with default perms is NOT owner-restricted on POSIX.

    On Windows, default tmp_path files inherit ACLs that grant more than just
    the current user (SYSTEM, Administrators), so the strict ``(F)``-only check
    in ``is_owner_restricted`` should return False until ``restrict_to_owner``
    runs. This guards against false-positive passes if the helper became a
    no-op.
    """
    p = tmp_path / "wide_open.txt"
    p.write_text("data")
    # On POSIX, tmp_path files are 0o644 by default. On Windows, ACLs are
    # inherited from the temp dir which grants more than just the current user.
    # Either way, is_owner_restricted should be False before restrict_to_owner.
    import os
    import sys
    if sys.platform != "win32":
        # Explicitly set 0o644 to make the precondition deterministic.
        os.chmod(p, 0o644)
    assert not is_owner_restricted(p)
