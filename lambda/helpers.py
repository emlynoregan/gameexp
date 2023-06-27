from fastapi import HTTPException
import base64
from shared import exc_to_string
from accesstoken import get_accesstoken
from user import get_user_rec
import requests
# import os
# import jwt

def get_accesstoken_rec_from_header(auth_header):
    access_token = None

    try:
        # Check if the header is present and starts with 'Bearer '
        if auth_header and auth_header.startswith('Bearer '):
            # Extract the encoded string
            # encoded_access_token = auth_header.split(' ')[1]
            # Decode the string
            # access_token = base64.b64decode(encoded_access_token).decode()
            access_token = auth_header.split(' ')[1]
            # print (f"access_token: {access_token}")
        else:
            print ("No Authorization header or it does not start with 'Bearer '")
    except Exception as e:
        print (exc_to_string(e))
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not access_token:
        # raise a 401 error
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token_rec = get_accesstoken(access_token)

    print (f"access_token_rec: {access_token_rec}")

    if not access_token_rec or not access_token_rec.get("owner_user_id"):
        # raise a 401 error
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return access_token_rec

async def get_resource(id, getf, resource_name, resource_to_apif, Authorization, test_authorization):
    access_token_rec = get_accesstoken_rec_from_header(Authorization or test_authorization)

    owner_user_id = access_token_rec.get("owner_user_id")

    rec = getf(id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"{resource_name} not found")

    if rec.get("owner_user_id") != owner_user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return resource_to_apif(rec)

async def list_resource(cursor, limit, listf, resource_name, resource_to_apif, to_list_typef, Authorization, test_authorization):
    access_token_rec = get_accesstoken_rec_from_header(Authorization or test_authorization)
    owner_user_id = access_token_rec.get("owner_user_id")

    limitint = int(limit) if limit else 100

    new_cursor, recs = listf(owner_user_id, cursor, limitint)

    recs = [resource_to_apif(rec) if resource_to_apif else rec for rec in recs]

    list = to_list_typef(recs, new_cursor)

    return list

async def update_resource(id, resource, getf, updatef, resource_name, resource_to_apif, Authorization, test_authorization):
    access_token_rec = get_accesstoken_rec_from_header(Authorization or test_authorization)

    owner_user_id = access_token_rec.get("owner_user_id")

    rec = getf(id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"{resource_name} not found")

    if rec.get("owner_user_id") != owner_user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    rec = updatef(id, resource)

    return resource_to_apif(rec)

async def delete_resource(id, getf, deletef, resource_name, to_delete_typef, Authorization, test_authorization):
    access_token_rec = get_accesstoken_rec_from_header(Authorization or test_authorization)

    owner_user_id = access_token_rec.get("owner_user_id")

    rec = getf(id)

    if not rec:
        raise HTTPException(status_code=404, detail=f"{resource_name} not found")

    if rec.get("owner_user_id") != owner_user_id:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # delete the credential
    deletef(id)

    # return the credential
    return to_delete_typef(id)

async def create_resource(createf, resource_to_apif, checkf=None, Authorization=None, test_authorization=None, **kwargs):
    access_token_rec = get_accesstoken_rec_from_header(Authorization or test_authorization)

    owner_user_id = access_token_rec.get("owner_user_id")

    # let's check that the user actually exists and is not disabled
    user_rec = get_user_rec(owner_user_id)

    if not (user_rec and not user_rec.get("disabled")):
        raise HTTPException(status_code=404, detail="User not found")

    if checkf:
        checkf(owner_user_id, **kwargs)

    rec = createf(owner_user_id, **kwargs)

    # return the credential
    return resource_to_apif(rec)


# class VerifyToken():
#     """Does all the token verification using PyJWT"""

#     def __init__(self, token):
#         self.token = token
#         self.config = {
#             "DOMAIN": os.getenv("auth0_domain"),
#             "API_AUDIENCE": os.getenv("auth0_audience"),
#             "ISSUER": os.getenv("auth0_issuer"),
#             "ALGORITHMS": os.getenv("auth0_algorithms"),
#         }

#         # This gets the JWKS from a given URL and does processing so you can
#         # use any of the keys available
#         jwks_url = f'https://{self.config["DOMAIN"]}/.well-known/jwks.json'
#         self.jwks_client = jwt.PyJWKClient(jwks_url)

#     def verify(self):
#         # This gets the 'kid' from the passed token
#         try:
#             self.signing_key = self.jwks_client.get_signing_key_from_jwt(
#                 self.token
#             ).key
#         except jwt.exceptions.PyJWKClientError as error:
#             return {"status": "error", "msg": error.__str__()}
#         except jwt.exceptions.DecodeError as error:
#             return {"status": "error", "msg": error.__str__()}

#         try:
#             payload = jwt.decode(
#                 self.token,
#                 self.signing_key,
#                 algorithms=self.config["ALGORITHMS"],
#                 audience=self.config["API_AUDIENCE"],
#                 issuer=self.config["ISSUER"],
#             )
#         except Exception as e:
#             return {"status": "error", "message": str(e)}

#         return payload

def get_jwks(endpoint):
    jwks = requests.get(endpoint).json()
    return jwks