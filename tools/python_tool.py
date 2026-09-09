from pydantic import BaseModel
from .registry import registry
import ast
import operator

class CalculateInput(BaseModel):
    expression: str

def calculate(expression: str) -> str:
    allowed_operators = {
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Mod: operator.mod, ast.USub: operator.neg,
    }
    def evaluate(node):
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)): return node.value
            raise ValueError("Only numbers are allowed.")
        if isinstance(node, ast.BinOp):
            left = evaluate(node.left)
            right = evaluate(node.right)
            operation = allowed_operators.get(type(node.op))
            if operation is None: raise ValueError("This mathematical operation is not allowed.")
            return operation(left, right)
        if isinstance(node, ast.UnaryOp):
            operation = allowed_operators.get(type(node.op))
            if operation is None: raise ValueError("This operation is not allowed.")
            return operation(evaluate(node.operand))
        raise ValueError("Invalid mathematical expression.")

    try:
        tree = ast.parse(expression, mode="eval")
        return str(evaluate(tree.body))
    except Exception as e:
        return f"Error: {e}"

registry.register("calculate", "Perform mathematical calculations. Use this tool whenever an exact numerical calculation is required.", calculate, CalculateInput, str)