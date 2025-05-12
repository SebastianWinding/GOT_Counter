# interface.py

from typing import Optional
# from pydantic import BaseModel
from webview import Window
# from tools.interface import expose

# class GreetInputData(BaseModel):
#     nickname: str
    
# class GreetInput(BaseModel):
#     name: str
#     data: GreetInputData

# class GreetOutput(BaseModel):
#     greeting: str

class API:
    window: Optional[Window] = None
    
    # @expose(GreetInput, GreetOutput)
    # def greet(self, data: GreetInput) -> GreetOutput:
    #     return GreetOutput(greeting=f"Hello, {data.name}!")

    # @expose(str, str)
    # def echo(self, text: str) -> str:
    #     return text
