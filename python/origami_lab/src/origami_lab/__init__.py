"""origami_lab: Origami strip kinematics and mental coupling analysis.

Provides SE(3) Lie group primitives, 1D origami strip forward kinematics,
V_4 symmetry projections, and mental coupling matrix estimation.
All numerical conventions match the TypeScript ``@kinemind/core-math`` package.
"""

from origami_lab.se3 import (
    SE3,
    quat_from_axis_angle,
    quat_mul,
    quat_conjugate,
    quat_normalize,
    quat_rotate,
    quat_to_mat3,
    se3_compose,
    se3_inverse,
    se3_apply,
    se3_identity,
    trans,
    rot,
)
from origami_lab.strip import (
    StripConfig,
    StripState,
    make_uniform_strip,
    flat_state,
    reflect_state,
    flip_state,
)
from origami_lab.kinematics import (
    CellPose,
    KinematicsResult,
    forward_kinematics,
)
from origami_lab.symmetry import (
    klein_four_strip,
    group_action,
    reynolds_project,
    equivariance_residual,
)
from origami_lab.coupling import (
    MentalCoupling,
    identity_coupling,
    mirror_coupling_matrix,
    apply_coupling,
    estimate_coupling,
    coupling_equivariance_residual,
    spectral_radius,
    effective_rank,
)

__all__ = [
    # se3
    "SE3",
    "quat_from_axis_angle",
    "quat_mul",
    "quat_conjugate",
    "quat_normalize",
    "quat_rotate",
    "quat_to_mat3",
    "se3_compose",
    "se3_inverse",
    "se3_apply",
    "se3_identity",
    "trans",
    "rot",
    # strip
    "StripConfig",
    "StripState",
    "make_uniform_strip",
    "flat_state",
    "reflect_state",
    "flip_state",
    # kinematics
    "CellPose",
    "KinematicsResult",
    "forward_kinematics",
    # symmetry
    "klein_four_strip",
    "group_action",
    "reynolds_project",
    "equivariance_residual",
    # coupling
    "MentalCoupling",
    "identity_coupling",
    "mirror_coupling_matrix",
    "apply_coupling",
    "estimate_coupling",
    "coupling_equivariance_residual",
    "spectral_radius",
    "effective_rank",
]
