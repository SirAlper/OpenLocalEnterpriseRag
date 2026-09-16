import ast
import operator
import re
import json
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from src.connectors.db_connector import DatabaseConnector

# Supported safe mathematical operators
_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval_ast(node):
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return node.value
        raise ValueError(f"Unsupported constant value: {node.value}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported operator: {op_type}")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Division by zero error!")
        return _OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Unsupported unary operator: {op_type}")
        return _OPERATORS[op_type](_eval_ast(node.operand))
    else:
        raise ValueError(f"Unsafe or invalid expression node: {type(node)}")


def safe_math_eval(expr_str: str) -> str:
    """Evaluate mathematical expression safely using AST parsing."""
    try:
        cleaned = re.sub(r"[^\d+\-*/().%]", "", expr_str.replace(",", "."))
        if not cleaned:
            return "No evaluable mathematical expression found."

        parsed = ast.parse(cleaned, mode="eval")
        result = _eval_ast(parsed.body)

        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 4)
        return str(result)
    except ZeroDivisionError:
        return "Error: Cannot divide by zero."
    except Exception as e:
        return f"Calculation error: {e}"


@tool("calculator", description="Performs arithmetic and mathematical calculations. Use for addition, subtraction, multiplication, division, and budget calculations.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions safely."""
    return safe_math_eval(expression)


# ──────────────────────────── DATABASE TOOLS ────────────────────────────

db_connector = DatabaseConnector()


@tool("sql_db_schema", description="Lists accessible tables and columns in the enterprise database. Use to inspect available tables and their schemas.")
def sql_db_schema(dummy: str = "") -> str:
    """Return the schema summary of the database."""
    if not db_connector.is_connected:
        return "Notice: Database connection is not configured or inactive."
    return db_connector.get_schema_summary()


@tool("sql_db_query", description="Executes a safe, read-only SQL SELECT query on the database. Use to query sales, products, inventory, orders, and numeric records.")
def sql_db_query(query: str) -> str:
    """Execute a safe, read-only SQL query against the database."""
    if not db_connector.is_connected:
        return "Error: Database connection is not active."

    res = db_connector.execute_query(query)
    if res["status"] != "success":
        return f"Error: {res.get('message', 'Query failed.')}"

    rows = res.get("rows", [])
    if not rows:
        return "Query executed successfully, but no matching rows were found."

    return json.dumps(rows, ensure_ascii=False, indent=2)


all_tools = [calc, sql_db_schema, sql_db_query]
tool_schema = [convert_to_openai_tool(t) for t in all_tools]
tools_by_name = {t.name: t for t in all_tools}
