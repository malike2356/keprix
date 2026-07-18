"""Generate a restrictive seccomp profile for the agent process.

Documented stub for MVP. Not applied automatically. Operators may wire this
through libseccomp or container runtime profiles when ready.
"""

from __future__ import annotations

ALLOWED_SYSCALLS = [
    # Memory
    "brk",
    "mmap",
    "mprotect",
    "munmap",
    "mremap",
    # I/O (controlled)
    "read",
    "write",
    "pread64",
    "pwrite64",
    "readv",
    "writev",
    "openat",
    "close",
    "lseek",
    "fstat",
    "stat",
    "newfstatat",
    # Network (egress controlled elsewhere)
    "socket",
    "connect",
    "bind",
    "listen",
    "accept",
    "accept4",
    "sendto",
    "recvfrom",
    "sendmsg",
    "recvmsg",
    "getsockname",
    "getpeername",
    "setsockopt",
    "getsockopt",
    # Process
    "clone",
    "clone3",
    "fork",
    "vfork",
    "execve",
    "execveat",
    "exit",
    "exit_group",
    "wait4",
    "getpid",
    "getppid",
    # Futex / threading
    "futex",
    "set_robust_list",
    "get_robust_list",
    # Time
    "clock_gettime",
    "gettimeofday",
    "nanosleep",
    # Signals (limited)
    "rt_sigaction",
    "rt_sigprocmask",
    "rt_sigreturn",
    "tgkill",
    "tkill",
    # Scheduler
    "sched_yield",
    "sched_getaffinity",
]

BLOCKED_SYSCALLS = [
    "ptrace",
    "init_module",
    "finit_module",
    "delete_module",
    "reboot",
    "kexec_load",
    "kexec_file_load",
    "mount",
    "umount2",
    "pivot_root",
    "chroot",
    "acct",
    "add_key",
    "request_key",
    "keyctl",
    "perf_event_open",
    "bpf",
]


def generate_seccomp_profile() -> str:
    """Return a textual stub profile (not raw BPF).

    Production would use libseccomp via python-seccomp or generate BPF bytecode.
    """
    allowed = ", ".join(ALLOWED_SYSCALLS)
    blocked = ", ".join(BLOCKED_SYSCALLS)
    return (
        "# seccomp filter stub: default KILL, whitelist approach\n"
        f"# allowed: {allowed}\n"
        f"# blocked: {blocked}\n"
        "# All syscalls not in ALLOWED list -> SIGKILL\n"
    )


def is_applied() -> bool:
    """MVP stub never auto-applies a filter."""
    return False
