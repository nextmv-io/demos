# Nextmv Order fulfillment with MIP

This model demonstrates how to solve an order fulfillment problem with a Mixed
Integer Programming problem using the open-source solver
[HiGHS](https://github.com/ERGO-Code/HiGHS).

To solve a Mixed Integer Problem (MIP) is to optimize a linear objective
function of many variables, subject to linear constraints.

Order fulfillment describes the logistical and organizational process of
fulfilling orders — from order placement to delivery confirmation. This includes
various decisions along this process. This model focuses on two aspects of the
order fulfillment problem: selecting the appropriate fulfillment center and the
carriers for transportation.

The input defines a number of order lines that are part of a single order. Each
order line has an ordered quantity and a volume per single item. Furthermore,
there is a definition of the fulfillment centers, with specific handling costs
and an inventory. For each fulfillment center, there are available carriers for
transportation, each having a definition of their capacity and their delivery
costs. Finally, there is a definition of the volume of a single box, which will
be used to package items.

The most important files created are `main.go` and the input files.

* `main.go` implements a MIP for the order fulfillment problem.
* `input_ofl_small.json` is a sample input file with a small instance (5 order
  lines, 2 fulfillment centers, 2 carriers at each center) that
  follows the input
  definition in
`main.go`.
* `input_ofl_medium.json` is a sample input file with a medium sized instance
  (15 order lines, 4 fulfillment centers, 2 carriers at each center) that
  follows the input
  definition in
`main.go`.
* `input_ofl_large.json` is a sample input file with a large instance (45 order
  lines, 6 fulfillment centers, 4 carriers at each center) that
  follows the input
  definition in
`main.go`.

Run the command below to see if everything works as expected:

```bash
nextmv run local . -- -runner.input.path input_ofl_small.json \
  -runner.output.path output.json -limits.duration 10s
```

A file `output.json` should have been created with the optimal order fulfillment
solution.

## Next steps

* Open `main.go` and read through the comments to understand the model.
* API documentation and examples can be found in the [package
  documentation](https://pkg.go.dev/github.com/nextmv-io/sdk/mip).
* Further documentation, guides, and API references about custom modelling and
deployment can also be found on our [blog](https://www.nextmv.io/blog) and on
our [documentation site](https://docs.nextmv.io).
* Need more assistance? Send us an [email](mailto:support@nextmv.io)!
