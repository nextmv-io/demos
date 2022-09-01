# Nextmv route template

`route` is a modeling kit for vehicle routing problems (VRP). This template
will get you up to speed deploying your own solution.

The most important files created are `main.go` and an input file.

`main.go` implements a VRP solver with many real world features already
configured. `input_blog.json` is a sample input for the use-case described in
our [blog post](https://www.nextmv.io/model-and-solve-a-custom-vrp-using-software-paradigms-with-a-food-retailer-example).

Before you start customizing run the command below to see if everything works as
expected:

```
nextmv sdk run main.go -- -hop.runner.input.path input_blog.json\
  -hop.runner.output.path output_blog.json
```

A file `output_blog.json` should have been created with a VRP solution.

## Next steps

* Open `main.go` and examine the options that are used for our blog-post.
* Chances are
  high that you need a different set of `route` options in your own use-case.
* In case you need some features that are not part of this example, such as
  precedence constraints, please take a look the package documentation of
  [route](https://pkg.go.dev/github.com/nextmv-io/sdk/route) for further
  guidence.
* Documentation, guides, and API reference about solving VRPs and deployment can
  also be found on our [blog](https://www.nextmv.io/blog) and on our
  [documentation site](https://docs.nextmv.io).
* Need more assistance? Send us an [email](mailto:support@nextmv.io)!
