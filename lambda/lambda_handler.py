# add /opt to the path, to get the libraries
import sys
sys.path.append('/opt')

from fastapi import FastAPI
import mangum

from spelunk_handler import spelunk_router

app = FastAPI()

# app.include_router(authn_router, prefix="/authn", tags=["authn"])
app.include_router(spelunk_router, prefix="/api/v1/spelunk", tags=["spelunk"])

handler = mangum.Mangum(app)
