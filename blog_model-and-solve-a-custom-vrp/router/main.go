package main

import (
	"strings"

	"github.com/nextmv-io/sdk/route"
	"github.com/nextmv-io/sdk/run"
	"github.com/nextmv-io/sdk/store"
)

func main() {
	run.Run(solver)
}

// This struct describes the expected json input by the runner.
// Features not needed can simply be deleted or commented out, but make
// sure that the corresponding option in `solver` is also commented out.
// In case you would like to support a different input format you can
// change the struct as you see fit. You may need to change some code in
// `solver` to use the new structure.
type input struct {
	Stops               []route.Stop         `json:"stops"`
	Vehicles            []string             `json:"vehicles"`
	Starts              []route.Position     `json:"starts"`
	Ends                []route.Position     `json:"ends"`
	Shifts              []route.TimeWindow   `json:"shift"`
	Penalties           []int                `json:"penalties"`
	Velocities          []float64            `json:"velocities"`
	ServiceTimes        []route.Service      `json:"service_times"`
	Classification      map[string]string    `json:"classification"`
	ImbalancePenalty	int					 `json:"imbalance_penalty"`
	UnassignedPenalty	int					 `json:"unassigned_penalty"`
}

type SizeClassificationConstraint struct {
	stops          []route.Stop
	classification map[string]string
}

// Violated implements route.VehicleConstraint
func (c SizeClassificationConstraint) Violated(vehicle route.PartialVehicle) (route.VehicleConstraint, bool) {
	var route = vehicle.Route()

	countLarge := 0

	// check stops, excluding start and end locations
	for i := 1; i < len(route)-1; i++ {
		var inIdx = route[i]
		stopName := c.stops[inIdx].ID

		if strings.ToLower(c.classification[stopName]) == "large" {
			countLarge = countLarge + 1
		}

		// more than one large store in a route => violation
		if countLarge > 1{
			return c, true
		}
	}

	return c, false
}

// Custom data to implement the VehicleUpdater interface.
type vehicleData struct {
}

// Update implements route.VehicleUpdater
func (d vehicleData) Update(s route.PartialVehicle) (route.VehicleUpdater, int, bool) {
	return d, 0, false
}

type fleetData struct {
	vehicleValues    map[string]int
	imbalancePenalty int
	fleetValue       int
	minLength		 int
	maxLength		 int
	unassignedStops  int
	unassignedPenalty int
}

// Update implements route.PlanUpdater
func (f fleetData) Update(p route.PartialPlan, v []route.PartialVehicle) (route.PlanUpdater, int, bool) {
	oldDiff := f.maxLength - f.minLength

	for i := 0; i < len(v); i++ {
		// Update value function information.
		vehicleID := v[i].ID()
		value := v[i].Value()

		_, ok := f.vehicleValues[vehicleID]
		if ok {
			f.fleetValue -= f.vehicleValues[vehicleID]
			f.vehicleValues[vehicleID] = value
			f.fleetValue += f.vehicleValues[vehicleID]
		} else {
			f.vehicleValues[vehicleID] = value
			f.fleetValue += f.vehicleValues[vehicleID]		
		}

		length := len(v[i].Route())

		if length > f.maxLength {
			f.maxLength = length
		}
		if length < f.minLength {
			f.minLength = length
		}
	}

	newDiff := f.maxLength - f.minLength
	f.fleetValue -= oldDiff * f.imbalancePenalty
	f.fleetValue += newDiff * f.imbalancePenalty
	
	f.fleetValue -= f.unassignedStops * f.unassignedPenalty
	f.unassignedStops = p.Unassigned().Len()
	f.fleetValue += f.unassignedStops * f.unassignedPenalty

	return f, f.fleetValue, true
}

// solver takes the input and solver options and constructs a routing solver.
// All route features/options depend on the input format. Depending on your
// goal you can add, delete or fix options or add more input validations. Please
// the [route package
// documentation](https://pkg.go.dev/github.com/nextmv-io/sdk/route) for further
// information on the options available to you.
func solver(i input, opt store.Options) (store.Solver, error) {
	// In case you directly expose the solver to untrusted, external input,
	// it is advisable from a security point of view to add strong
	// input validations before passing the data to the solver.

	// Define custom constraint
	constraint := SizeClassificationConstraint{stops: i.Stops, classification: i.Classification}
	
	// prepare custom value function
	v := vehicleData{}
	vehicleValues := make(map[string]int, len(i.Vehicles))
	
	f := fleetData{imbalancePenalty: i.ImbalancePenalty, 
		minLength: len(i.Stops), maxLength: 0, vehicleValues: vehicleValues, 
		unassignedStops: 0, unassignedPenalty: i.UnassignedPenalty}

	// Define base router.
	router, err := route.NewRouter(
		i.Stops,
		i.Vehicles,
		route.Threads(1),
		route.Velocities(i.Velocities),
		route.Starts(i.Starts),
		route.Ends(i.Ends),
		route.Services(i.ServiceTimes),
		route.Shifts(i.Shifts),
		route.Unassigned(i.Penalties),
		route.Constraint(constraint, i.Vehicles),
		route.Update(v, f),
	)
	if err != nil {
		return nil, err
	}

	// You can also fix solver options like the expansion limit below.
	opt.Diagram.Expansion.Limit = 1

	return router.Solver(opt)
}
