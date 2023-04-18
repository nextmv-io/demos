// package main holds the implementation of the routing template.
package main

import (
	"log"
	"math"
	"time"

	"github.com/nextmv-io/sdk/route"
	"github.com/nextmv-io/sdk/run"
	"github.com/nextmv-io/sdk/run/encode"
	"github.com/nextmv-io/sdk/store"
)

func main() {
	err := run.Run(solver,
		run.Encode[run.CLIRunnerConfig, input](
			GenericEncoder[store.Solution, store.Options](encode.JSON()),
		),
	)
	if err != nil {
		log.Fatal(err)
	}
}

// This struct describes the expected json input by the runner.
// Features not needed can simply be deleted or commented out, but make
// sure that the corresponding option in `solver` is also commented out.
// In case you would like to support a different input format you can
// change the struct as you see fit. You may need to change some code in
// `solver` to use the new structure.
type input struct {
	Stops              []route.Stop       `json:"stops"`
	Vehicles           []string           `json:"vehicles"`
	Starts             []route.Position   `json:"starts"`
	Ends               []route.Position   `json:"ends"`
	Quantities         []int              `json:"quantities"`
	Capacities         []int              `json:"capacities"`
	Precedences        []route.Job        `json:"precedences"`
	Velocities         []float64          `json:"velocities"`
	ServiceTimes       []route.Service    `json:"service_times"`
	Shifts             []route.TimeWindow `json:"shifts"`
	EarlinessPenalties []int              `json:"earliness_penalties"`
	LatenessPenalties  []int              `json:"lateness_penalties"`
	TargetTimes        []time.Time        `json:"target_times"`
	Labels             []Label            `json:"labels"`
}

// solver takes the input and solver options and constructs a routing solver.
// All route features/options depend on the input format. Depending on your
// goal you can add, delete or fix options or add more input validations. Please
// see the [route package
// documentation](https://pkg.go.dev/github.com/nextmv-io/sdk/route) for further
// information on the options available to you.
func solver(i input, opts store.Options) (store.Solver, error) {
	// In case you directly expose the solver to untrusted, external input,
	// it is advisable from a security point of view to add strong
	// input validations before passing the data to the solver.

	stopMap := make(map[int]route.Stop)
	labelMap := make(map[string]bool)
	precedenceMap := make(map[string]string)
	for idx, s := range i.Stops {
		stopMap[idx] = s
	}
	for _, l := range i.Labels {
		labelMap[l.ID] = true
	}
	for _, p := range i.Precedences {
		precedenceMap[p.PickUp] = p.DropOff
	}

	p := planData{
		earlinessPenalties: i.EarlinessPenalties,
		latenessPenalties:  i.LatenessPenalties,
		targetTimes:        i.TargetTimes,
		stops:              i.Stops,
		labelMap:           labelMap,
		precedenceMap:      precedenceMap,
	}
	v := vehicleData{
		earlinessPenalties: i.EarlinessPenalties,
		latenessPenalties:  i.LatenessPenalties,
		targetTimes:        i.TargetTimes,
	}

	// Define base router.
	router, err := route.NewRouter(
		i.Stops,
		i.Vehicles,
		route.Velocities(i.Velocities),
		route.Starts(i.Starts),
		route.Ends(i.Ends),
		route.Shifts(i.Shifts),
		route.Capacity(i.Quantities, i.Capacities),
		route.Precedence(i.Precedences),
		route.Services(i.ServiceTimes),
		route.Update(v, p),
	)
	if err != nil {
		return nil, err
	}

	router.Format(outputFormat(p))

	// You can also fix solver options like the expansion limit below.
	opts.Diagram.Expansion.Limit = 1
	// A duration limit of 0 is treated as infinity. For cloud runs you need to
	// set an explicit duration limit which is why it is currently set to 10s
	// here in case no duration limit is set. For local runs there is no time
	// limitation. If you want to make cloud runs for longer than 5 minutes,
	// please contact: support@nextmv.io
	if opts.Limits.Duration == 0 {
		opts.Limits.Duration = 10 * time.Second
	}

	return router.Solver(opts)
}

// vehicleData implements the route.VehicleUpdater interface.
type vehicleData struct {
	earlinessPenalties []int
	latenessPenalties  []int
	targetTimes        []time.Time
}

func (v vehicleData) Update(
	s route.PartialVehicle,
) (route.VehicleUpdater, int, bool) {
	earliness := 0
	lateness := 0
	totalDuration := 0
	etas := s.Times().EstimatedArrival
	etds := s.Times().EstimatedDeparture
	// Loop over all stops in the route and update earliness penalty when
	// arriving before the ETA and the lateness penalty when arriving after.
	for i, r := range s.Route() {
		totalDuration += etds[len(etds)-1] - etas[0]
		if r < len(v.targetTimes) {
			target := int(v.targetTimes[r].Unix())
			earliness += int(
				math.Max(float64(target-etas[i]), 0.0),
			) * v.earlinessPenalties[r]
			lateness += int(
				math.Max(float64(etas[i]-target), 0.0),
			) * v.latenessPenalties[r]
		}
	}

	return v, totalDuration + earliness + lateness, true
}

// planData implements the PlanUpdater interface.
type planData struct {
	earlinessPenalties []int
	latenessPenalties  []int
	targetTimes        []time.Time
	stops              []route.Stop
	vehicleValues      map[string]int
	planValue          int
	labelMap           map[string]bool
	precedenceMap      map[string]string
}

func (d planData) Update(
	s route.PartialPlan,
	vehicles []route.PartialVehicle,
) (route.PlanUpdater, int, bool) {
	// Perform a safe copy of the vehicle values map.
	values := make(map[string]int, len(d.vehicleValues))
	for vehicleID, i := range d.vehicleValues {
		values[vehicleID] = i
	}
	d.vehicleValues = values

	// Update the values for the vehicles that changed.
	for _, vehicle := range vehicles {
		vehicleID := vehicle.ID()
		value := vehicle.Value()
		d.planValue -= d.vehicleValues[vehicleID]
		d.vehicleValues[vehicleID] = value
		d.planValue += d.vehicleValues[vehicleID]
	}

	return d, d.planValue, true
}

// Custom Format
func outputFormat(d planData) func(p *route.Plan) any {
	return func(p *route.Plan) any {
		output := make(map[string]any)
		vehicles := make([]any, len(p.Vehicles))
		var totalEarliness, totalLateness, totalDuration, lifoViolations int
		for v, vehicle := range p.Vehicles {
			route := make([]any, len(vehicle.Route))
			for i, stop := range vehicle.Route {
				var target *time.Time
				earliness := 0
				lateness := 0

				// The vehicle's start and end location are not important.
				if i != 0 && i != len(vehicle.Route)-1 {
					// Check for LIFO violations.
					lifo := d.labelMap[stop.ID]
					nextStop := vehicle.Route[i+1]
					if lifo && nextStop.ID != d.precedenceMap[stop.ID] {
						lifoViolations++
					}
					// Get the indexof the stop.
					stopIndex := -1
					for j, s := range d.stops {
						if s.ID == stop.ID {
							stopIndex = j
							break
						}
					}
					if stopIndex == -1 {
						panic("stop not found")
					}

					eta := int(stop.EstimatedArrival.Unix())
					target = &d.targetTimes[stopIndex]
					targetUnix := int(target.Unix())
					earliness = int(
						math.Max(float64(targetUnix-eta), 0.0),
					) * d.earlinessPenalties[stopIndex]
					lateness = int(
						math.Max(float64(eta-targetUnix), 0.0),
					) * d.latenessPenalties[stopIndex]
				}

				totalEarliness += earliness
				totalLateness += lateness
				route[i] = map[string]any{
					"id":                  stop.ID,
					"position":            stop.Position,
					"estimated_arrival":   stop.EstimatedArrival,
					"estimated_departure": stop.EstimatedDeparture,
					"estimated_service":   stop.EstimatedService,
					"target":              target,
					"earliness":           earliness,
					"lateness":            lateness,
				}
			}

			vehicles[v] = map[string]any{
				"id":             vehicle.ID,
				"route":          route,
				"route_duration": vehicle.RouteDuration,
				"route_distance": vehicle.RouteDistance,
			}
			totalDuration += vehicle.RouteDuration
		}

		output["unassigned"] = p.Unassigned
		output["vehicles"] = vehicles
		output["lateness"] = totalLateness
		output["earliness"] = totalEarliness
		output["total_duration"] = totalDuration
		output["num_lifo_violations"] = lifoViolations

		return output
	}
}

type Label struct {
	ID    string `json:"id"`
	Label string `json:"label"`
}
