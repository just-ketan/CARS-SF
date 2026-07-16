"""
Education Application Registry

Central registry of all education application profiles.

Author: RSNSD
"""

from .attendance_system import ATTENDANCE_SYSTEM
from .digital_library import DIGITAL_LIBRARY
from .interactive_whiteboard import INTERACTIVE_WHITEBOARD
from .learning_management import LEARNING_MANAGEMENT
from .live_classroom import LIVE_CLASSROOM
from .online_exam import ONLINE_EXAM
from .smart_classroom import SMART_CLASSROOM
from .teacher_portal import TEACHER_PORTAL


# ==========================================================
# Registry
# ==========================================================

EDUCATION_PROFILE_REGISTRY = [

    LIVE_CLASSROOM,

    ONLINE_EXAM,

    DIGITAL_LIBRARY,

    LEARNING_MANAGEMENT,

    SMART_CLASSROOM,

    ATTENDANCE_SYSTEM,

    TEACHER_PORTAL,

    INTERACTIVE_WHITEBOARD,

]

# ==========================================================
# Sampling Weights
# ==========================================================

EDUCATION_PROFILE_WEIGHTS = [

    0.25,   # Live Classroom

    0.08,   # Online Examination

    0.15,   # Digital Library

    0.18,   # LMS

    0.10,   # Smart Classroom

    0.08,   # Attendance

    0.08,   # Teacher Portal

    0.08,   # Interactive Whiteboard

]

assert abs(sum(EDUCATION_PROFILE_WEIGHTS) - 1.0) < 1e-6