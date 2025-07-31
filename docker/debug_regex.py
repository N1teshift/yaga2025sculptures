import re

ctx = {}
ice_pass = "mysecret"
text = 'password="{{ icecast_source_password | default("hackme") }}"'

def repl(m):
    expr = m.group(1).strip()
    parts = [p.strip() for p in expr.split("|")]
    var = parts[0]
    default = None
    for p in parts[1:]:
        m2 = re.match(r'default\((["\'])(.*?)\1\s*\)', p.strip())
        if m2:
            default = m2.group(2)
    print(f"  expr={expr!r}")
    print(f"  parts={parts}")
    print(f"  var={var!r}")
    print(f"  default={default!r}")
    if var in ctx:
        return str(ctx[var])
    if "." in var:
        base, sub = var.split(".", 1)
        if base in ctx and isinstance(ctx[base], dict) and sub in ctx[base]:
            return str(ctx[base][sub])
    if var == "control_host":
        return os.environ.get("CONTROL_HOST", "localhost")
    if default is not None:
        return default
    return m.group(0)

pat = r"{{\s*([\w.\s|()\'\"\']+)\s*}}"
result = re.sub(pat, repl, text)
print(f"result={result!r}")
