# interface.py

from typing import Optional, List
from pydantic import BaseModel
from webview import Window
from tools.interface import expose

class GreetInputData(BaseModel):
    nickname: str
    
class GreetInput(BaseModel):
    name: Optional[str]
    data: List[GreetInputData]

class GreetOutput(BaseModel):
    greeting: str

class API:    
    # @expose(GreetInput, GreetOutput)
    # def greet(self, data: GreetInput) -> GreetOutput:
    #     return GreetOutput(greeting=f"Hello, {data.name}!")

    @expose(str, str)
    def echo(self, text: str) -> str:
        return text
