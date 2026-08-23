"""
Testet classify_moment und das neue "on <TT.MM.JJJJ>"-Vokabular (23.08.).
Kostenlos, kein API-Key nötig. Exakt das Szenario aus dem Contract:
ein Ereignis am 20.08., geprüft an drei verschiedenen query_time-Punkten.
"""

from datetime import datetime

from tcl.query import classify_moment
from tcl.temporal_engine import normalize


def check(name: str, got, expected) -> None:
    status = "OK" if got == expected else "FAIL"
    marker = "✓" if status == "OK" else "✗"
    print(f"[{marker} {status}] {name}: got={got}, expected={expected}")
    assert got == expected, f"{name}: expected {expected}, got {got}"


def main() -> None:
    print("=== 'on 20.08.2026' korrekt aufgelöst ===")
    interval = normalize("on 20.08.2026", assertion_time=datetime(2026, 8, 17))
    check("start == 20.08.2026", interval.start, datetime(2026, 8, 20))
    check("end == start (echter Punkt)", interval.end, interval.start)

    print("\n=== Drei Zeitpunkte gegen dasselbe Ereignis (20.08.) ===")
    check("17.08. (3 Tage vorher) -> upcoming", classify_moment(interval, datetime(2026, 8, 17)), "upcoming")
    check("20.08. (am Tag selbst) -> due", classify_moment(interval, datetime(2026, 8, 20)), "due")
    check("23.08. (danach) -> past", classify_moment(interval, datetime(2026, 8, 23)), "past")

    print("\n=== Regressionsschutz: kein Datum bekannt -> unknown ===")
    unknown_interval = normalize("im März", assertion_time=datetime(2026, 8, 17))
    check("nicht erkannter Ausdruck -> unknown", classify_moment(unknown_interval, datetime(2026, 8, 20)), "unknown")

    print("\nAlle Checks bestanden.")


if __name__ == "__main__":
    main()