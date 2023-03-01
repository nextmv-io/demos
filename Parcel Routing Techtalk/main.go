// package main holds the implementation of the routing template.
package main

import (
	"log"
	"time"

	"github.com/nextmv-io/sdk/measure"
	"github.com/nextmv-io/sdk/route"
	"github.com/nextmv-io/sdk/run"
	"github.com/nextmv-io/sdk/store"
)

func main() {
	err := run.Run(solver)
	if err != nil {
		log.Fatal(err)
	}
}

// These structs describe the expected json input for the model.
// Features not needed can simply be deleted or commented out, but make
// sure that the corresponding option in `solver` is also commented out.
// In case you would like to support additional options or constraints
// you can change the schema to suit those. You will need to change the code
// below to extract the new input data into the proper structs for the engine.
type input struct {
	Stops         []Stop        `json:"stops"`
	Vehicles      []Vehicle     `json:"vehicles"`
	Configuration Configuration `json:"configuration"`
}

type Vehicle struct {
	ID      string   `json:"id"`
	Backlog []string `json:"backlog"`
}

type Stop struct {
	route.Stop
	HardWindow route.TimeWindow `json:"hard_window"`
	Type       string           `json:"package_type"`
}

type Configuration struct {
	Depot              route.Position   `json:"depot"`
	Shift              route.TimeWindow `json:"driver_shift"`
	InitializationCost int              `json:"initialization_cost"`
	Capacity           int              `json:"capacity"`
	Speed              int              `json:"speed"`
	Quantity           int              `json:"quantity"`
	Duration           int              `json:"duration"`
	Penalty            int              `json:"unassigned_penalty"`
	MaxWait            int              `json:"max_wait"`
	SolverRunTime      int              `json:"runtime"`
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

	// First we will create a few helper variables and a set of data structures
	// which are compatible with the Router engine.
	var stopCount = len(i.Stops)
	var vehicleCount = len(i.Vehicles)
	var maxWait = -1
	if i.Configuration.MaxWait >= 0 {
		maxWait = i.Configuration.MaxWait
	}

	stops := make([]route.Stop, stopCount)
	vehicles := make([]string, vehicleCount)
	depots := make([]route.Position, vehicleCount)
	quantities := make([]int, stopCount)
	capacities := make([]int, vehicleCount)
	stopDurations := make([]route.Service, stopCount)
	shifts := make([]route.TimeWindow, vehicleCount)
	windows := make([]route.Window, stopCount)
	penalties := make([]int, stopCount)
	initializationCosts := make([]float64, vehicleCount)
	backlogs := make([]route.Backlog, 0)
	points := make([]measure.Point, 0)
	stopTypes := make([]string, stopCount)

	// Now we need to populate these internal data structures with our input
	// data.
	for s, stop := range i.Stops {
		stops[s] = stop.Stop
		quantities[s] = i.Configuration.Quantity
		penalties[s] = i.Configuration.Penalty
		points = append(points, measure.Point{stop.Position.Lon, stop.Position.Lat})
		stopDurations[s] = route.Service{ID: stop.ID, Duration: i.Configuration.Duration}
		if stop.Type != "" {
			stopTypes[s] = stop.Type
		}
		// Not all stops may have time windows, so these are conditional.
		if stop.HardWindow != (route.TimeWindow{}) {
			windows[s] = route.Window{TimeWindow: stop.HardWindow, MaxWait: maxWait}
		}
	}

	for v, vehicle := range i.Vehicles {
		vehicles[v] = vehicle.ID
		depots[v] = i.Configuration.Depot
		capacities[v] = i.Configuration.Capacity
		shifts[v] = i.Configuration.Shift
		initializationCosts[v] = float64(i.Configuration.InitializationCost)
		points = append(points, measure.Point{i.Configuration.Depot.Lon, i.Configuration.Depot.Lat})
		points = append(points, measure.Point{i.Configuration.Depot.Lon, i.Configuration.Depot.Lat})

		// Vehicles won't always have a backlog, so this are conditional
		if len(vehicle.Backlog) > 0 {
			backlogs = append(backlogs, route.Backlog{VehicleID: vehicle.ID, Stops: vehicle.Backlog})
		}
	}

	// Since we want to explicitly optimize for duration rather than distance, we
	// will create a duration measure. This one uses Haversine, but this is
	// easily adaptable to accept a matrix input built from your chosen provider
	// of distance & duration data. More information about available measures is
	// available [in our docs](https://www.nextmv.io/docs/how-to-guides/router#measures---cost).
	distance := measure.HaversineByPoint()
	distanceIndexed := route.Indexed(distance, points)
	timeMeasures := make([]route.ByIndex, vehicleCount)

	for m := range timeMeasures {
		timeMeasures[m] = measure.Scale(distanceIndexed, 1.0/float64(i.Configuration.Speed))
	}

	// We need to create the custom type needed for our custom constraint interface.
	typeConstraint := CustomConstraint{types: stopTypes}

	// Now we define our router with the constraints and options we've selected.
	router, err := route.NewRouter(
		stops,
		vehicles,
		route.Starts(depots),
		route.Ends(depots),
		route.Services(stopDurations),
		route.Shifts(shifts),
		route.Capacity(quantities, capacities),
		route.InitializationCosts(initializationCosts),
		route.Backlogs(backlogs),
		route.Unassigned(penalties),
		route.Windows(windows),
		route.ValueFunctionMeasures(timeMeasures),
		route.TravelTimeMeasures(timeMeasures),
		route.Constraint(typeConstraint, vehicles),
	)
	if err != nil {
		return nil, err
	}

	// You can also fix solver options like the expansion limit below.
	opts.Diagram.Expansion.Limit = 1
	// A duration limit of 0 is treated as infinity. For cloud runs you need to
	// set an explicit duration limit, which can accept a value passed in via
	// your input schema. Here we default to 10 seconds if no time is For local runs there is no time
	// limitation. If you want to make cloud runs for longer than 5 minutes,
	// please contact: support@nextmv.io
	if i.Configuration.SolverRunTime != 0 {
		opts.Limits.Duration = time.Duration(i.Configuration.SolverRunTime) * time.Second
	} else {
		opts.Limits.Duration = 10 * time.Second
	}

	return router.Solver(opts)
}

// CustomConstraint is a custom type that implements Violated to fulfill the
// VehicleConstraint interface.
type CustomConstraint struct {
	types []string
}

// Violated the method that must be implemented to be a used as a
// VehicleConstraint. This checks to ensure only packages of the same type are
// on a route.
func (c CustomConstraint) Violated(
	vehicle route.PartialVehicle,
) (route.VehicleConstraint, bool) {
	route := vehicle.Route()

	// If only one stop is assigned, the constraint is feasible.
	if len(route) <= 3 {
		return c, false
	}

	// Omit the start and end locations of the vehicle and the first stop.
	locations := route[2 : len(vehicle.Route())-1]

	// Get the label of the first stop assigned to the route.
	label := c.types[route[1]]
	for _, location := range locations {
		// If the labels don't match, the constraint is violated.
		if len(c.types) > 1 {
			if label != c.types[location] {
				return c, true
			}
		}
	}

	return c, false
}
