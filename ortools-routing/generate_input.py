"""Generate VRP inputs for the tuning demo.

The shipped community-app input has 10 stops / 2 vehicles and solves in
milliseconds, so no amount of strategy tuning changes the answer. This module
builds deterministic, capacity-constrained instances with enough structure that
the first-solution strategy and local-search metaheuristic produce meaningfully
different routes within a few seconds -- which is the whole point of the demo.

`build_instance()` is parameterized so a suite of varied inputs can be generated
(see experiment_suite.py) to show that the *best* strategy changes with the
input -- the core justification for ensembles.

Run:  python generate_input.py > input.json
"""

import argparse
import json
import math
import random
import sys
from typing import Any

DEPOT = {"lon": 7.625, "lat": 51.9622}  # Muenster, DE


def build_instance(
    n_stops: int = 150,
    n_vehicles: int = 10,
    seed: int = 42,
    geography: str = "clustered",  # "clustered" | "uniform"
    n_neighborhoods: int = 6,
    cluster_spread: float = 0.006,  # ~0.65 km std dev within a neighborhood
    area_radius: float = 0.045,  # ~5 km spread of the service area
    capacity_factor: float = 1.15,  # fleet capacity / total demand
    max_hours: float = 4.0,
    speed: float = 8.0,  # m/s (~29 km/h urban)
    service_seconds: int = 120,
) -> dict[str, Any]:
    """Builds one VRP instance. Deterministic given the seed."""
    rng = random.Random(seed)

    if geography == "clustered":
        # Random neighborhood centers within the service area; stops gauss around them.
        centers = [
            (
                rng.uniform(-area_radius, area_radius),
                rng.uniform(-area_radius, area_radius),
            )
            for _ in range(n_neighborhoods)
        ]

        def sample():
            cx, cy = rng.choice(centers)
            return (cx + rng.gauss(0, cluster_spread), cy + rng.gauss(0, cluster_spread))

    elif geography == "uniform":
        # Stops spread evenly across a disk -- no clustering structure.
        def sample():
            r = area_radius * math.sqrt(rng.random())
            theta = rng.uniform(0, 2 * math.pi)
            return (r * math.cos(theta), r * math.sin(theta))

    else:
        raise ValueError(f"Unknown geography '{geography}'.")

    stops = []
    for i in range(n_stops):
        dx, dy = sample()
        stops.append(
            {
                "id": f"stop-{i + 1}",
                "location": {
                    "lon": round(DEPOT["lon"] + dx, 6),
                    "lat": round(DEPOT["lat"] + dy, 6),
                },
                "quantity": rng.randint(1, 3),
                "duration": service_seconds,
            }
        )

    total_demand = sum(s["quantity"] for s in stops)
    capacity = math.ceil(total_demand * capacity_factor / n_vehicles)

    vehicles = [
        {
            "id": f"vehicle-{v + 1}",
            "capacity": capacity,
            "speed": speed,
            "start_location": DEPOT,
            "end_location": DEPOT,
            "max_duration": int(max_hours * 60 * 60),
        }
        for v in range(n_vehicles)
    ]

    return {"vehicles": vehicles, "stops": stops}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stops", type=int, default=150)
    parser.add_argument("--vehicles", type=int, default=10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--geography", choices=["clustered", "uniform"], default="clustered")
    parser.add_argument("--neighborhoods", type=int, default=6)
    parser.add_argument("--capacity-factor", type=float, default=1.15)
    parser.add_argument("--max-hours", type=float, default=4.0)
    args = parser.parse_args()

    instance = build_instance(
        n_stops=args.stops,
        n_vehicles=args.vehicles,
        seed=args.seed,
        geography=args.geography,
        n_neighborhoods=args.neighborhoods,
        capacity_factor=args.capacity_factor,
        max_hours=args.max_hours,
    )
    total_demand = sum(s["quantity"] for s in instance["stops"])
    cap = instance["vehicles"][0]["capacity"]
    sys.stderr.write(
        f"stops={args.stops} vehicles={args.vehicles} geography={args.geography} "
        f"total_demand={total_demand} capacity/vehicle={cap} fleet_capacity={cap * args.vehicles}\n"
    )
    json.dump(instance, sys.stdout, indent=2)


if __name__ == "__main__":
    main()
