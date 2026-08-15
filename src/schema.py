from typing import Optional, Literal
from pydantic import BaseModel

PropertyType = Literal["residential", "commercial", "retail", "industrial", "other"]
RentFreq     = Literal["monthly", "annual", "weekly", "other"]

class LeaseFields(BaseModel):
    landlord_name:      Optional[str]          = None
    tenant_name:        Optional[str]          = None
    property_address:   Optional[str]          = None
    property_type:      Optional[PropertyType] = None
    premises_area_sqft: Optional[float]        = None
    lease_start_date:   Optional[str]          = None   # ISO YYYY-MM-DD
    lease_end_date:     Optional[str]          = None   # ISO YYYY-MM-DD
    term_length_months: Optional[int]          = None
    base_rent_amount:   Optional[float]        = None
    rent_frequency:     Optional[RentFreq]     = None

FIELDS = list(LeaseFields.model_fields.keys())
