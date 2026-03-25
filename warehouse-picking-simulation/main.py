import random

import mesa
import nextmv
import numpy as np

from visuals import build_timeline_chart, build_utilization_chart


class OrderAgent(mesa.Agent):
    """Represents an incoming order waiting to be picked."""

    def __init__(self, model, items: int):
        super().__init__(model)
        self.items = items
        self.arrival_step = model.steps
        self.assigned = False
        self.completed = False
        self.wait_time = 0  # steps from arrival to pickup start

    def step(self):
        pass


class PickerAgent(mesa.Agent):
    """A warehouse picker that claims and fulfills orders."""

    def __init__(self, model, pick_duration: int):
        super().__init__(model)
        self.pick_duration = pick_duration  # steps per item
        self.current_order = None
        self.steps_remaining = 0
        self.busy_steps = 0

    def step(self):
        if self.current_order is not None:
            # Working on an order
            self.steps_remaining -= 1
            self.busy_steps += 1
            if self.steps_remaining <= 0:
                self.current_order.completed = True
                self.model.orders_completed += 1
                self.current_order = None
        else:
            # Try to claim the next unclaimed order
            pending = [
                a for a in self.model.agents
                if isinstance(a, OrderAgent) and not a.assigned and not a.completed
            ]
            if pending:
                order = min(pending, key=lambda o: o.arrival_step)
                order.assigned = True
                order.wait_time = self.model.steps - order.arrival_step
                self.model.total_wait_time += order.wait_time
                self.model.orders_started += 1
                self.current_order = order
                self.steps_remaining = order.items * self.pick_duration
                self.busy_steps += 1


class WarehouseModel(mesa.Model):
    """Warehouse simulation with picker and order agents."""

    def __init__(
        self,
        num_pickers: int,
        order_arrival_rate: float,
        pick_duration: int,
        items_per_order: int,
        seed: int | None = None,
    ):
        super().__init__(seed=seed)
        self.order_arrival_rate = order_arrival_rate
        self.items_per_order = items_per_order
        self.orders_completed = 0
        self.orders_started = 0
        self.total_wait_time = 0
        self.steps = 0
        self.rng = np.random.default_rng(seed)

        # Per-step history for timeline chart
        self.history = []

        # Create pickers
        for _ in range(num_pickers):
            PickerAgent(self, pick_duration)

    def step(self):
        self.steps += 1

        # Spawn new orders via Poisson process
        num_arrivals = self.rng.poisson(self.order_arrival_rate)
        for _ in range(num_arrivals):
            OrderAgent(self, self.items_per_order)

        # Run all agents
        self.agents.shuffle_do("step")

        # Record snapshot
        pending_count = sum(
            1 for a in self.agents
            if isinstance(a, OrderAgent) and not a.completed
        )
        self.history.append({
            "step": self.steps,
            "orders_completed": self.orders_completed,
            "orders_pending": pending_count,
        })


def main():
    manifest = nextmv.Manifest.from_yaml(".")
    options = manifest.extract_options()

    input_data = nextmv.load(options=options, path=options.input)
    data = input_data.data or {}

    nextmv.redirect_stdout()

    seed = options.random_seed if options.random_seed else None

    model = WarehouseModel(
        num_pickers=options.num_pickers,
        order_arrival_rate=options.order_arrival_rate,
        pick_duration=options.pick_duration,
        items_per_order=options.items_per_order,
        seed=seed,
    )

    nextmv.log(f"Running simulation: {options.num_pickers} pickers, "
               f"{options.num_steps} steps, "
               f"arrival_rate={options.order_arrival_rate}")

    for _ in range(options.num_steps):
        model.step()

    # Compute metrics
    pickers = [a for a in model.agents if isinstance(a, PickerAgent)]
    total_picker_steps = options.num_steps * len(pickers)
    busy_steps = sum(p.busy_steps for p in pickers)
    picker_utilization = busy_steps / total_picker_steps if total_picker_steps > 0 else 0.0

    avg_wait_time = (
        model.total_wait_time / model.orders_started
        if model.orders_started > 0 else 0.0
    )
    throughput = model.orders_completed / options.num_steps

    orders_pending = sum(
        1 for a in model.agents
        if isinstance(a, OrderAgent) and not a.completed
    )

    nextmv.log(f"Orders completed: {model.orders_completed}, pending: {orders_pending}")
    nextmv.log(f"Picker utilization: {picker_utilization:.2%}, throughput: {throughput:.3f}/step")

    picker_utilizations = [
        {"picker_id": i, "utilization": p.busy_steps / options.num_steps}
        for i, p in enumerate(pickers)
    ]

    timeline_chart = build_timeline_chart(model.history)
    utilization_chart = build_utilization_chart(picker_utilizations)

    output = nextmv.Output(
        solution={
            "orders_completed": model.orders_completed,
            "orders_pending": orders_pending,
            "picker_utilizations": picker_utilizations,
            "history": model.history,
        },
        assets=[timeline_chart, utilization_chart],
        metrics={
            "orders_completed": model.orders_completed,
            "orders_pending": orders_pending,
            "avg_wait_time": round(avg_wait_time, 2),
            "picker_utilization": round(picker_utilization, 4),
            "throughput": round(throughput, 4),
        },
    )

    nextmv.write(output, path=options.output)


if __name__ == "__main__":
    main()
