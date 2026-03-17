# Nextmv Parcel Routing Techtalk

This model has been adapted from the Nextmv `routing` template to
suit common constraints and requirements for parcel delivery.
To learn more about its contents, be sure to watch [our
 techtalk on the subject](https://www.nextmv.io/videos/route-optimization-for-package-and-parcel-delivery).

The most important files created are `main.go` and `input.json`.

`main.go` implements a VRP solver with many real world features common to
routing parcel and package delivery already configured. `input.json` is a sample
input file that follows the input definition in `main.go`, and
`input-backlogs.json` represents a re-planning of the output from `input.json`
with added packages to deliver and vehicle backlogs applied.

Before you start customizing run the command below to see if everything works as
expected:

```bash
nextmv run local . -- -runner.input.path input.json\
  -runner.output.path output.json
```

A file `output.json` should have been created with a VRP solution.

## Next steps

* For more information about our platform, please visit: <https://nextmv.io/docs>.
* Need more assistance? Send us an [email](mailto:support@nextmv.io)!
