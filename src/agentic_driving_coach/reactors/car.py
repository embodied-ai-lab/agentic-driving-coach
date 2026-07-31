"""Car reactor: point-mass longitudinal dynamics.

Physics preserved from the Car reactor in StopSign.lf (agentic-driving-coach):
each incoming action maps to a net acceleration (messages.ACCELERATION_MAP),
integrated with a semi-implicit Euler step of ``dt`` seconds:

    v  <-  max(0, v + a * dt)
    x  <-  x + v * dt

A coach actuation command arriving at the same tag as driver input overrides
the corresponding driver channel (brake commands override the brake channel,
acceleration commands the accelerator channel), exactly as in the original.
"""

from __future__ import annotations

from collections.abc import Callable

import xronos

from ..messages import ACCELERATION_MAP, DriverAction


def step_velocity(velocity: float, action: DriverAction | None, dt: float) -> float:
    """One integration step used by the reactor."""
    acceleration = ACCELERATION_MAP[action] if action is not None else 0.0
    return max(0.0, velocity + acceleration * dt)


class Car(xronos.Reactor):
    accelerator_in = xronos.InputPortDeclaration[DriverAction]()
    brake_in = xronos.InputPortDeclaration[DriverAction]()
    actuate_in = xronos.InputPortDeclaration[DriverAction]()

    velocity = xronos.OutputPortDeclaration[float]()
    #: The action actually applied this step, after any coach override.
    applied_action = xronos.OutputPortDeclaration[DriverAction]()

    def __init__(self, initial_velocity: float, dt: float) -> None:
        super().__init__()
        self._velocity = initial_velocity
        self._distance_travelled = 0.0
        self._dt = dt

    @property
    def distance_travelled(self) -> float:
        return self._distance_travelled

    @xronos.reaction
    def drive(self, ctx: xronos.ReactionContext) -> Callable[[], None]:
        accelerator = ctx.add_trigger(self.accelerator_in)
        brake = ctx.add_trigger(self.brake_in)
        actuate = ctx.add_trigger(self.actuate_in)
        velocity_out = ctx.add_effect(self.velocity)
        applied_out = ctx.add_effect(self.applied_action)

        def handler() -> None:
            accel_cmd = accelerator.get() if accelerator.is_present() else None
            brake_cmd = brake.get() if brake.is_present() else None

            if actuate.is_present():
                override = actuate.get()
                if override.is_brake:
                    brake_cmd = override
                else:
                    accel_cmd = override

            # Brake input takes precedence over the accelerator, as in the
            # original if/elif chain.
            action = brake_cmd if brake_cmd is not None else accel_cmd

            self._velocity = step_velocity(self._velocity, action, self._dt)
            self._distance_travelled += self._velocity * self._dt

            velocity_out.set(self._velocity)
            if action is not None:
                applied_out.set(action)

        return handler
