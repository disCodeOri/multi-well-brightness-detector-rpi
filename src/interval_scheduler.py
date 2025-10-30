# src/interval_scheduler.py

import threading
import time
from copy import deepcopy

class IntervalScheduler(threading.Thread):
    """
    Manages a complex recording schedule in a separate thread.
    Communicates with the main UI thread via thread-safe callbacks.
    """
    def __init__(self, schedule_config, callbacks):
        """
        Initializes the scheduler.

        Args:
            schedule_config (dict): A dictionary containing 'phases' and 'repeat_count'.
            callbacks (dict): A dictionary of callback functions for UI updates.
                              Expected keys: 'on_phase_change', 'on_tick', 
                                             'on_complete', 'on_error'.
        """
        super().__init__(daemon=True)
        self.schedule = deepcopy(schedule_config)
        self.callbacks = callbacks
        self._stop_event = threading.Event()

    def run(self):
        """The main loop for the scheduler thread."""
        try:
            phases = self.schedule.get("phases", [])
            if not phases:
                raise ValueError("Schedule contains no phases.")
            # New semantics:
            # - 'repeat_count' in schedule_config represents additional repeats
            #   beyond the first run (e.g. 0 -> one iteration, 1 -> two iterations)
            # - 'infinite_repeat' (bool) controls whether the schedule runs forever
            repeat_count = int(self.schedule.get("repeat_count", 0))
            is_infinite = bool(self.schedule.get("infinite_repeat", False))

            # total_cycles is number of full cycles to perform when not infinite
            total_cycles = None if is_infinite else (repeat_count + 1)

            cycle_num = 0
            # Loop until stop requested and cycles completed (or infinite)
            while not self._stop_event.is_set() and (is_infinite or cycle_num < total_cycles):
                cycle_num += 1
                for phase_index, phase in enumerate(phases):
                    if self._stop_event.is_set(): break

                    phase_name = phase.get("name", f"Phase {phase_index + 1}")
                    action = phase.get("action", "wait")
                    duration = phase.get("duration", 0)

                    # Notify UI of phase change
                    # Keep the callback signature the same: pass the configured
                    # 'repeat_count' (additional repeats) so the UI can decide how
                    # to display cycles. UI can also check the schedule for
                    # 'infinite_repeat' if needed.
                    self.callbacks['on_phase_change'](
                        phase_name, duration, cycle_num, repeat_count, action
                    )

                    # Countdown loop for the current phase
                    for t in range(duration, 0, -1):
                        if self._stop_event.is_set(): break
                        self.callbacks['on_tick'](t)
                        time.sleep(1) # Wait for one second
                    
                    if self._stop_event.is_set(): break

            if not self._stop_event.is_set():
                self.callbacks['on_complete']()

        except Exception as e:
            self.callbacks['on_error'](f"Scheduler error: {e}")

    def stop(self):
        """Signals the scheduler thread to stop."""
        self._stop_event.set()