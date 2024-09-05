# def auto_repr(cls):
#     def __repr__(self):
#         attributes = {
#             key: value
#             for key, value in vars(self).items()
#             if not key.startswith("__") and not callable(value)
#         }
#         attr_str = ", ".join(f"{key}={repr(value)}" for key, value in attributes.items())
#         return f"{cls.__name__}({attr_str})"

#     cls.__repr__ = __repr__
#     return cls


def auto_repr(cls):
    cls.__repr__ = (
        lambda self: f"{self.__class__.__name__}({", ".join(f"{k}={getattr(self, k)}" for k in self.__dict__)})"
    )
    return cls
