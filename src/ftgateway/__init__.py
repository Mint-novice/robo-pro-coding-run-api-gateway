"""Fischertechnik Run API Gateway ROBO Pro Coding project toolkit.

Read, generate and verify `.ft` project files (they are plain ZIP archives),
plus an optional Chrome-DevTools-Protocol bridge that drives the real
ROBO Pro Coding application.

Public API::

    from ftgateway import Project, build_motor_run, verify

    project = build_motor_run("Motor_Run", speed=512)
    project.save("Motor_Run.ft")
    print(verify("Motor_Run.ft"))
"""

from .project import Project, ProjectError
from .blocks import (
    ProjectBuilder,
    build_led_blink,
    build_led_steady,
    build_motor_run,
    build_python_project,
)
from .verify import verify, VerifyResult

__version__ = "0.1.0"

__all__ = [
    "Project",
    "ProjectError",
    "ProjectBuilder",
    "build_motor_run",
    "build_led_blink",
    "build_led_steady",
    "build_python_project",
    "verify",
    "VerifyResult",
    "__version__",
]
