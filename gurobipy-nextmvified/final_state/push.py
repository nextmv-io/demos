import os

from nextmv.cloud import Application, Client

api_key = os.environ.get("NEXTMV_API_KEY")
if api_key is None:
    raise Exception("Please set NEXTMV_API_KEY environment variable")

client = Client(api_key=api_key)
if Application.exists(client, id="gurobipy-example"):
    app = Application(client=client, id="gurobipy-example")
else:
    app = Application.new(client=client, id="gurobipy-example", name="Gurobi Example")


app_dir = os.path.dirname(os.path.abspath(__file__))
app.push(app_dir=app_dir, verbose=True)
