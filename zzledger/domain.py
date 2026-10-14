"""账本格式与数据校验，不依赖窗口或文件系统。"""
def validate_ledger(data):
    from datetime import date
    def integer(value):
        return type(value) is int and abs(value) <= 999999999999
    def category(value):
        return isinstance(value, str) and value == value.strip() and 0 < len(value) <= 20 and not any(ord(ch) < 32 or ord(ch) == 127 for ch in value)
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("accounts"), list) or not isinstance(data.get("entries"), list):
        raise ValueError("账本格式不正确")
    ids = set()
    custom = data.get("customCategories", [])
    if not isinstance(custom, list) or any(not category(c) for c in custom) or len(set(custom)) != len(custom):
        raise ValueError("自定义分类数据无效")
    for a in data["accounts"]:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"] or a["id"] in ids or not isinstance(a.get("name"), str) or not a["name"].strip() or len(a["name"]) > 30 or a.get("type") not in ("微信", "支付宝", "银行卡", "现金", "其他") or not integer(a.get("balance")):
            raise ValueError("账户数据无效")
        ids.add(a["id"])
    entries = set()
    debts = data.get("debts", [])
    if not isinstance(debts, list):
        raise ValueError("待还款数据格式不正确")
    debt_ids = set()
    for d in debts:
        if not isinstance(d, dict) or not isinstance(d.get("id"), str) or not d["id"] or d["id"] in debt_ids or not isinstance(d.get("name"), str) or not d["name"].strip() or len(d["name"]) > 50 or not isinstance(d.get("creditor"), str) or len(d["creditor"]) > 50 or not integer(d.get("amount")) or d["amount"] <= 0 or not isinstance(d.get("dueDate"), str) or not isinstance(d.get("note"), str) or len(d["note"]) > 200:
            raise ValueError("待还款明细无效")
        if d["dueDate"] and date.fromisoformat(d["dueDate"]).isoformat() != d["dueDate"]:
            raise ValueError("还款日期无效")
        debt_ids.add(d["id"])
    paid = dict.fromkeys(debt_ids, 0)
    for e in data["entries"]:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"] or e["id"] in entries or e.get("accountId") not in ids or e.get("kind") not in ("expense", "income") or not integer(e.get("amount")) or e["amount"] <= 0 or not category(e.get("category")) or not isinstance(e.get("note"), str) or len(e["note"]) > 200:
            raise ValueError("收支记录无效")
        if not isinstance(e.get("date"), str) or date.fromisoformat(e["date"]).isoformat() != e["date"]:
            raise ValueError("日期无效")
        entries.add(e["id"])
        if "debtId" in e:
            if not isinstance(e["debtId"], str) or e["debtId"] not in debt_ids or e["kind"] != "expense" or e["category"] != "还款":
                raise ValueError("还款记录关联无效")
            paid[e["debtId"]] += e["amount"]
    for d in debts:
        if paid[d["id"]] > d["amount"]:
            raise ValueError("还款金额不能超过应还总额")
    return data


