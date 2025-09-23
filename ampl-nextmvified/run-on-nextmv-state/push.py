import os

from nextmv.cloud import Application, Client

# import sys


api_key = os.environ.get("NEXTMV_API_KEY")
if api_key is None:
    raise Exception("Please set NEXTMV_API_KEY environment variable")

# version_id = None
# if len(sys.argv) > 1:
#     version_id = sys.argv[1]
# else:
#     version_id = os.environ.get("VERSION_ID")

# if version_id is None:
#     raise Exception(
#         "Please provide VERSION_ID either as command line argument or environment variable"
#     )

client = Client(api_key=api_key)
if Application.exists(client, id="ampl-example"):
    app = Application(client=client, id="ampl-example")
else:
    app = Application.new(client=client, id="ampl-example", name="AMPL Example")


app_dir = os.path.dirname(os.path.abspath(__file__))
app.push(app_dir=app_dir, verbose=True)
# app.new_version(id=version_id, name=version_id)
# if app.instance_exists("staging"):
#     app.update_instance(version_id=version_id, id="staging", name="staging")
# else:
#     app.new_instance(version_id=version_id, id="staging", name="staging")
