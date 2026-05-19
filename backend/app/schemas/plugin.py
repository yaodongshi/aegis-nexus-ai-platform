from pydantic import BaseModel

class PluginBase(BaseModel):
    name: str
    description: str

class PluginCreate(PluginBase):
    pass

class PluginRead(PluginBase):
    id: int
