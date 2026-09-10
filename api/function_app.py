import azure.functions as func

from blueprints import admin, auth, documents, laboratory

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
for blueprint in (auth.bp, admin.bp, laboratory.bp, documents.bp):
    app.register_functions(blueprint)
