from fastapi import APIRouter, FastAPI, Request, HTTPException, Header
from typing import Optional
from pydantic import BaseModel
from spelunk import get_spelunk_by_id, create_spelunk_rec_from_url, Spelunk, get_spelunk_rec, spelunk_rec_needs_processing, add_temporary_urls_to_spelunk_rec
from shared import process_op_in_blambda
import os

spelunk_router = APIRouter()

class SpelunkCreate(BaseModel):
    url: str

@spelunk_router.post("")
async def create_spelunk(values: SpelunkCreate) -> Spelunk:
    s3_bucket = os.environ['bucket_name']

    spelunk_rec = create_spelunk_rec_from_url(values.url)

    if spelunk_rec:
        if spelunk_rec_needs_processing(spelunk_rec):
            spelunk_id = spelunk_rec['id']
            process_op_in_blambda(spelunk_id, 'process_spelunk', {"spelunk_id": spelunk_id})
    
        spelunk_rec = add_temporary_urls_to_spelunk_rec(spelunk_rec, s3_bucket)

        return Spelunk(**spelunk_rec)
    else:
        raise HTTPException(status_code=500, detail="Failed to create spelunk")
 
@spelunk_router.get("/{spelunk_id}")
async def get_spelunk(spelunk_id: str) -> Spelunk:
    s3_bucket = os.environ['bucket_name']

    spelunk_rec = get_spelunk_rec(spelunk_id)

    if spelunk_rec:
        if spelunk_rec_needs_processing(spelunk_rec):
            process_op_in_blambda(spelunk_id, 'process_spelunk', {"spelunk_id": spelunk_id})

        spelunk_rec = add_temporary_urls_to_spelunk_rec(spelunk_rec, s3_bucket)

        return Spelunk(**spelunk_rec)
    else:
        raise HTTPException(status_code=404, detail="Spelunk not found")


