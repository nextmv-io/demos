// package main holds the implementation of the mip-knapsack template.
package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"time"

	"github.com/nextmv-io/sdk/mip"
	"github.com/nextmv-io/sdk/model"
	"github.com/nextmv-io/sdk/run"
)

// This is a Integer Programming model to solve the order fulfillment problem.
// We created this model, by initializing the mip-knapsack template from the
// nextmv CLI first and then modifying it to this specific use case.
// This mip-knapsack template demonstrates how to solve a Mixed Integer
// Programming problem. To solve a mixed integer problem is to optimize a linear
// objective function of many variables, subject to linear constraints.
// The order fulfillment problem is a typical decision problem in e-commerce and
// the retailer industry. Whenever multiple fulfillment centers are available to
// fulfill an order, it needs to be determined, which one is actually used.
// Furthermore, it might be necessary to determine, which carrier is used to
// transport the order from the fulfillment center to the customer if there is
// more than one option.
func main() {
	err := run.CLI(solver).Run(context.Background())
	if err != nil {
		log.Fatal(err)
	}
}

type input struct {
	Items          		[]item 							`json:"items"`
	WeightCapacity 		int    							`json:"weightCapacity"`
	FulfillmentCenters	[]fulfillmentCenter				`json:"fulfillmentCenters"`
	CarrierCapacities	map[string]map[string]float64	`json:"carrierCapacities"`
	DeliveryCosts		map[string]map[string]float64	`json:"deliveryCosts"`
	CartonVolume		float64							`json:"cartonVolume"`
}

// An item has a unique ID, an ordered quantity and a volume
type item struct {
	ItemID 			string  	`json:"itemId"`
	Quantity		float64 	`json:"quantity"`
	Volume			float64		`json:"volume"`
}

// ID is implemented to fulfill the model.Identifier interface.
func (i item) ID() string {
	return i.ItemID
}

type fulfillmentCenter struct{
	FulfillmentCenterId	string			`json:"fulfillmentCenterId"`
	Inventory			map[string]int	`json:"inventory"`
	HandlingCost		float64			`json:"handlingCost"`
}

func (i fulfillmentCenter) ID() string {
	return i.FulfillmentCenterId
}

type carrier struct{
	FulfillmentCenter	fulfillmentCenter		`json:"fulfillmentCenter"`
	Carrier				string					`json:"carrier"`
}

func (i carrier) ID() string{
	return i.FulfillmentCenter.FulfillmentCenterId + "-" + i.Carrier
}

type assignment struct{
	Item				item				`json:"item"`
	FulfillmentCenter	fulfillmentCenter	`json:"fulfillmentCenter"`
	Carrier				string				`json:"carrier"`
	Quantity 			int					`json:"quantity"`
}

func (i assignment) ID() string{
	return i.Item.ItemID + "-" + i.FulfillmentCenter.FulfillmentCenterId + "-" + i.Carrier + "-" + fmt.Sprint(i.Quantity)
}

// The Option for the solver.
type Option struct {
	// A duration limit of 0 is treated as infinity. For cloud runs you need to
	// set an explicit duration limit which is why it is currently set to 10s
	// here in case no duration limit is set. For local runs there is no time
	// limitation. If you want to make cloud runs for longer than 5 minutes,
	// please contact: support@nextmv.io
	Limits struct {
		Duration time.Duration `json:"duration" default:"10s"`
	} `json:"limits"`
}

// Output is the output of the solver.
type Output struct {
	Status  	string  			`json:"status,omitempty"`
	Runtime 	string  			`json:"runtime,omitempty"`
	Items   	[]item  			`json:"items,omitempty"`
	Value   	float64 			`json:"value,omitempty"`
	Assignments []assignment 		`json:"assignments"`
	Cartons 	map[string]float64 	`json:"cartons"`
}

func computeAssignments(input input) []assignment{
	assignments := []assignment{}
	for _, it := range input.Items{
		for _, fc := range input.FulfillmentCenters{
			for c := range input.CarrierCapacities[fc.FulfillmentCenterId]{
				for q := 0; q < int(it.Quantity); q++{
					newAssignment := assignment{
						Item: it,
						FulfillmentCenter: fc,
						Carrier: c,
						Quantity: q+1,
					}
					assignments = append(assignments, newAssignment)
				}
			}
		}
	}
	return assignments
}

func solver(input input, opts Option) ([]Output, error) {
	// We start by creating a MIP model.
	m := mip.NewModel()

	// create assignments (item, fc, carrier combinations)
	assignments := computeAssignments(input)

	// create some helping data structures
	fulfillmentCenterCarrierCombinations := []carrier{}
	for _, fc := range input.FulfillmentCenters{
		for c := range input.CarrierCapacities[fc.FulfillmentCenterId]{
			newCarrier := carrier{
				FulfillmentCenter: fc,
				Carrier: c,
			}
			fulfillmentCenterCarrierCombinations = append(fulfillmentCenterCarrierCombinations, newCarrier)
		}
	}

	itemToAssignments := make(map[string][]assignment, len(input.Items))
	fulfillmentCenterToCarrierToAssignments := make(map[string]map[string][]assignment, len(input.FulfillmentCenters))
	for _, as := range assignments{
		itemId := as.Item.ItemID
		_, ok := itemToAssignments[itemId]
		if !ok{
			itemToAssignments[itemId] = []assignment{}
		}
		itemToAssignments[itemId] = append(itemToAssignments[itemId], as)
		_, ok = fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId]
		if !ok{
			fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId] = make(map[string][]assignment)
		}
		_, ok = fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId][as.Carrier]
		if !ok{
			fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId][as.Carrier] = []assignment{}
		}
		fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId][as.Carrier] = append(fulfillmentCenterToCarrierToAssignments[as.FulfillmentCenter.FulfillmentCenterId][as.Carrier], as)
	}
	
	// x is a multimap representing a set of variables. It is initialized with a
	// create function and, in this case one set of elements. The elements can
	// be used as an index to the multimap. To retrieve a variable, call
	// x.Get(element) where element is an element from the index set.
	x := model.NewMultiMap(
		func(...assignment) mip.Bool{
			return m.NewBool()
		}, assignments)

	// create another multimap which will hold the info about the number of
	// cartons at each distribution center
	cartons := model.NewMultiMap(
		func(...carrier) mip.Float{
			return m.NewFloat(0.0, 1000.0)
		}, fulfillmentCenterCarrierCombinations)

	// We want to maximize the value of the knapsack.
	m.Objective().SetMinimize()

	/* Fulfilment constraint -> ensure all items are assigned */
	for _, i := range input.Items{
		fulfillment := m.NewConstraint(
			mip.Equal,
			i.Quantity,
		)
		for _, a := range itemToAssignments[i.ItemID]{
			fulfillment.NewTerm(float64(a.Quantity), x.Get(a))
		}
	}

	/* Carrier capacity constraint -> consider the carrier capacities in the
	solution; carrier capacity is considered in volume */
	for fcId, v := range fulfillmentCenterToCarrierToAssignments{
		for cId, list := range v{
			carrier := m.NewConstraint(
				mip.LessThanOrEqual,
				input.CarrierCapacities[fcId][cId],
			)
			for _, as := range list{
				carrier.NewTerm(as.Item.Volume * as.Item.Quantity, x.Get(as))
			}
		}
	}

	/* Inventory constraint -> Consider the inventory of each item at the
	distribution centers */
	for _, i := range input.Items{
		for _, fc := range input.FulfillmentCenters{
			inventory := m.NewConstraint(
				mip.LessThanOrEqual,
				float64(fc.Inventory[i.ItemID]),
			)
			for _, a := range itemToAssignments[i.ItemID]{
				if a.FulfillmentCenter.FulfillmentCenterId == fc.FulfillmentCenterId{
					inventory.NewTerm(float64(a.Quantity), x.Get(a))
				}
			}
		}
	}

	/* carton computation -> look at every distribution center and accumulate
	the volume of all the assigned items, use the carton volume from the input to
	compute the number of cartons that are necessary */
	for _, fc := range fulfillmentCenterCarrierCombinations{
		cartonConstr := m.NewConstraint(
			mip.Equal,
			0.0,
		)
		cartonConstr.NewTerm(-1, cartons.Get(fc))
		for _, a := range assignments{
			if a.FulfillmentCenter.FulfillmentCenterId == fc.FulfillmentCenter.FulfillmentCenterId && a.Carrier == fc.Carrier{
				cartonConstr.NewTerm(a.Item.Volume * float64(a.Quantity) * 1/input.CartonVolume, x.Get(a))
			}
		}
	}

	/* objective function = handling costs + delivery costs */
	/* handling costs: cost is based on number of cartons that need to be
	handled at a distribution center */
	/* delivery costs: cost is based on number of cartons that need to be
	transported */
	for _, combination := range fulfillmentCenterCarrierCombinations {
		m.Objective().NewTerm(input.DeliveryCosts[combination.FulfillmentCenter.FulfillmentCenterId][combination.Carrier], cartons.Get(combination))		// delivery costs
		m.Objective().NewTerm(combination.FulfillmentCenter.HandlingCost, cartons.Get(combination))	// handling costs
	}

	// We create a solver using the 'highs' provider
	solver, err := mip.NewSolver("highs", m)
	if err != nil {
		return nil, err
	}

	// We create the solve options we will use
	solveOptions := mip.NewSolveOptions()

	// Limit the solve to a maximum duration
	if err = solveOptions.SetMaximumDuration(opts.Limits.Duration); err != nil {
		return nil, err
	}

	// Set the relative gap to 0% (highs' default is 5%)
	if err = solveOptions.SetMIPGapRelative(0); err != nil {
		return nil, err
	}

	// Set verbose level to see a more detailed output
	solveOptions.SetVerbosity(mip.Off)

	solution, err := solver.Solve(solveOptions)
	if err != nil {
		return nil, err
	}

	output, err := format(solution, input, x, assignments, fulfillmentCenterCarrierCombinations, cartons)
	if err != nil {
		return nil, err
	}

	return []Output{output}, nil
}

func format(
	solution mip.Solution,
	input input,
	x model.MultiMap[mip.Bool, assignment],
	assignments []assignment,
	carriers []carrier,
	cartons model.MultiMap[mip.Float, carrier],
) (output Output, err error) {
	output.Status = "infeasible"
	output.Runtime = solution.RunTime().String()

	if solution != nil && solution.HasValues() {
		if solution.IsOptimal() {
			output.Status = "optimal"
		} else {
			output.Status = "suboptimal"
		}

		output.Value = solution.ObjectiveValue()

		assignmentList := make([]assignment,0)
		for _, assignment := range assignments {
			if solution.Value(x.Get(assignment)) > 0.5{
				assignmentList = append(assignmentList, assignment)
			}
		}

		output.Assignments = assignmentList

		output.Cartons = make(map[string]float64)
		for _, c := range carriers{
			output.Cartons[c.FulfillmentCenter.FulfillmentCenterId+"-"+c.Carrier] = solution.Value(cartons.Get(c))
		}
	} else {
		return output, errors.New("no solution found")
	}

	return output, nil
}
