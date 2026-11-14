"""Child process: runs a solution against several test cases without tracing.

Run as:  python -E -s judge_runner.py  < {"code", "prelude", "drivers": [...], "timeout"}
Writes {"syntax": {...}} or {"cases": [{"status", "result", "stdout", "error"}]}.
"""
from __future__ import annotations

import io
import json
import signal
import sys

FILENAME = "<user>"
MAX_TIMEOUTS = 2


class CaseTimeout(BaseException):
    pass


def _alarm(_sig, _frm):
    raise CaseTimeout()


def main():
    req = json.loads(sys.stdin.read())
    real_stdout = sys.stdout
    try:
        code_obj = compile(req["code"], FILENAME, "exec")
    except SyntaxError as e:
        real_stdout.write(json.dumps({"syntax": {
            "type": type(e).__name__, "msg": e.msg, "line": e.lineno or 1}}))
        return
    prelude_obj = compile(req.get("prelude") or "", "<prelude>", "exec")
    timeout = float(req.get("timeout", 2.0))
    can_alarm = hasattr(signal, "setitimer")
    if can_alarm:
        signal.signal(signal.SIGALRM, _alarm)

    cases = []
    timeouts = 0
    for driver in req["drivers"]:
        if timeouts >= MAX_TIMEOUTS:
            cases.append({"status": "skipped"})
            continue
        out = io.StringIO()
        ns = {"__name__": "__main__", "__builtins__": __builtins__}
        case: dict = {"status": "ok"}
        sys.stdout = out
        try:
            if can_alarm:
                signal.setitimer(signal.ITIMER_REAL, timeout)
            exec(prelude_obj, ns)
            exec(code_obj, ns)
            exec(compile(driver, "<driver>", "exec"), ns)
            if can_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
            case["result"] = repr(ns.get("__wdib_result__"))[:20_000]
        except CaseTimeout:
            case["status"] = "timeout"
            timeouts += 1
        except BaseException as e:
            if can_alarm:
                signal.setitimer(signal.ITIMER_REAL, 0)
            line = None
            tb = e.__traceback__
            while tb is not None:
                if tb.tb_frame.f_code.co_filename == FILENAME:
                    line = tb.tb_lineno
                tb = tb.tb_next
            case["status"] = "error"
            case["error"] = {"type": type(e).__name__, "msg": str(e)[:300], "line": line}
        finally:
            sys.stdout = real_stdout
        case["stdout"] = out.getvalue()[:2000]
        cases.append(case)
    real_stdout.write(json.dumps({"cases": cases}))


if __name__ == "__main__":
    main()
