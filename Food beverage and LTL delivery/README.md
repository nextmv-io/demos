# Route optimization for food, beverage, and less-than-truckload (LTL) delivery

This model uses the `routing` template, which provides a modeling kit for
vehicle routing problems (VRP). 

The most important files are `main.go` and `input_techtalk.json`.

`main.go` implements a VRP solver with many real world features already
configured. `input_techtalk.json` is a sample input file that follows the input
definition in `main.go`.

The folder `experiments` contains four more input files that are variations of
the `input_techtalk.json` input.

Before you start customizing run the command below to see if everything works as
expected:

```bash
nextmv sdk run . -- -runner.input.path input.json\
  -runner.output.path output.json -limits.duration 10s
```
The file `new-value-function.txt` contains code snippets that can be used to add
a custom value function to the model. This is a very basic example of such a
custom value function and is only used for demonstration purposes.

## Next steps

* For more information about our platform, please visit: <https://docs.nextmv.io>.
* Need more assistance? Send us an [email](mailto:support@nextmv.io)!
