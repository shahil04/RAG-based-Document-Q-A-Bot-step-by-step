from datetime import datetime

from pydantic import BaseModel


class DocumentResponse(BaseModel):

    id: int
    filename: str
    file_type: str
    file_size: int
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }