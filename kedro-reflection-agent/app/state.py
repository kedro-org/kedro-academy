"""Demo state machine.

The dashboard walks through:
    idle -> run_1_done -> reflected -> applied -> run_2_done

Buttons in each step are gated by the current state so the demo can only be
clicked through in order.
"""
