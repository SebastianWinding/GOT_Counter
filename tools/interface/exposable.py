from functools import wraps
from inspect   import isclass
from typing    import Any, Optional, Type
from pydantic  import BaseModel

def expose(
    in_model:  Optional[Type[BaseModel]] = None,
    out_model: Optional[Type[BaseModel]] = None
):
    """
    Decorator that:
      • casts raw dict → in_model if given
      • dumps out_model → dict if given
      • automatically skips `self` when applied to instance methods
    """
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args: Any) -> Any:
            # the last arg is always the payload from JS
            raw = args[-1]

            # 1) parse input
            if in_model and isclass(in_model) and issubclass(in_model, BaseModel):
                data = in_model(**raw)
            else:
                data = raw

            # 2) call your original fn
            #    if it's a method, args[0] is self
            if len(args) == 1:
                result = fn(data)
            else:
                result = fn(args[0], data)

            # 3) serialize output
            if out_model and isclass(out_model) and issubclass(out_model, BaseModel):
                return result.model_dump(mode="json")
            return result

        return wrapped

    return decorator
