from sqlalchemy.ext.compiler import compiles
from sqlalchemy.types import ARRAY

@compiles(ARRAY, "sqlite")
def compile_array_sqlite(type_, compiler, **kw):
    return "JSON"

# from sqlalchemy.schema import Column
# from sqlalchemy.types import (
#     Integer,
#     String,
#     TypeDecorator,
#     )
# from sqlalchemy import Sequence
# import json
#
# class ArrayType(TypeDecorator):
#     """ Sqlite-like does not support arrays.
#         Let's use a custom type decorator.
#
#         See http://docs.sqlalchemy.org/en/latest/core/types.html#sqlalchemy.types.TypeDecorator
#     """
#     impl = String
#
#     def process_bind_param(self, value, dialect):
#         return json.dumps(value)
#
#     def process_result_value(self, value, dialect):
#         return json.loads(value)
#
#     def copy(self):
#         return ArrayType(self.impl.length)
