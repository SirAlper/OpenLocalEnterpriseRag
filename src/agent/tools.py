import ast
import operator
import re
import json
from langchain_core.tools import tool
from langchain_core.utils.function_calling import convert_to_openai_tool
from src.connectors.db_connector import DatabaseConnector

# Desteklenen güvenli matematiksel operatörler
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
        raise ValueError(f"Desteklenmeyen sabit değer: {node.value}")
    elif isinstance(node, ast.BinOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Desteklenmeyen operatör: {op_type}")
        left = _eval_ast(node.left)
        right = _eval_ast(node.right)
        if op_type in (ast.Div, ast.FloorDiv, ast.Mod) and right == 0:
            raise ZeroDivisionError("Sıfıra bölme hatası!")
        return _OPERATORS[op_type](left, right)
    elif isinstance(node, ast.UnaryOp):
        op_type = type(node.op)
        if op_type not in _OPERATORS:
            raise ValueError(f"Desteklenmeyen tekil operatör: {op_type}")
        return _OPERATORS[op_type](_eval_ast(node.operand))
    else:
        raise ValueError(f"Güvensiz veya geçersiz ifade türü: {type(node)}")


def safe_math_eval(expr_str: str) -> str:
    """Matematiksel ifadeyi güvenli bir şekilde hesaplar."""
    try:
        # Sayı ayracı olarak kullanılan noktaları ve virgülleri düzenle
        cleaned = re.sub(r"[^\d+\-*/().%]", "", expr_str.replace(",", "."))
        if not cleaned:
            return "Hesaplanabilir matematiksel ifade bulunamadı."

        parsed = ast.parse(cleaned, mode="eval")
        result = _eval_ast(parsed.body)

        if isinstance(result, float) and result.is_integer():
            result = int(result)
        elif isinstance(result, float):
            result = round(result, 4)
        return str(result)
    except ZeroDivisionError:
        return "Hata: Sayılar sıfıra bölünemez."
    except Exception as e:
        return f"Hesaplama hatası ({e})"


@tool("calculator", description="Aritmetik ve matematiksel hesaplamaları gerçekleştirir. Toplama, çıkarma, çarpma, bölme, bütçe hesaplamaları için kullanın.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions safely."""
    return safe_math_eval(expression)


# ──────────────────────────── VERİTABANI ARAÇLARI ────────────────────────────

db_connector = DatabaseConnector()


@tool("sql_db_schema", description="Şirket veritabanındaki erişilebilir tabloları ve kolonları listeler. Hangi tablonun veya kolonun mevcut olduğunu kontrol etmek için kullanın.")
def sql_db_schema(dummy: str = "") -> str:
    """Return the schema summary of the database."""
    if not db_connector.is_connected:
        return "Bilgi: Veritabanı bağlantısı yapılandırılmamış veya aktif değil."
    return db_connector.get_schema_summary()


@tool("sql_db_query", description="Veritabanında salt-okunur (read-only) SQL SELECT sorgusu çalıştırır. Satış, ürün, stok, sipariş ve sayısal verileri sorgulamak için kullanın.")
def sql_db_query(query: str) -> str:
    """Execute a safe, read-only SQL query against the database."""
    if not db_connector.is_connected:
        return "Hata: Veritabanı bağlantısı aktif değil."

    res = db_connector.execute_query(query)
    if res["status"] != "success":
        return f"Hata: {res.get('message', 'Sorgu başarısız.')}"

    rows = res.get("rows", [])
    if not rows:
        return "Sorgu başarıyla çalıştı ancak eşleşen sonuç bulunamadı."

    return json.dumps(rows, ensure_ascii=False, indent=2)


all_tools = [calc, sql_db_schema, sql_db_query]
tool_schema = [convert_to_openai_tool(t) for t in all_tools]
tools_by_name = {t.name: t for t in all_tools}
