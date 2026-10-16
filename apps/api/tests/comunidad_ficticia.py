"""Comunidad ficticia "Mirador de Curauma" para pruebas del motor.

Dos torres (A y B) de 8 departamentos. Prorrateos proporcionales a la superficie
(62,5 m², 78,3 m² y 104,9 m² en el último piso), con 8 decimales y suma exacta 1.
B-202 y B-302 quedan una cienmillonésima bajo sus pares, como ocurre en reglamentos reales.
"""

from decimal import Decimal

from app.services.prorrateo import normalizar_prorrateos

PRORRATEOS: dict[str, Decimal] = {
    "A-101": Decimal("0.04943056"),  # 62,5 m²
    "A-102": Decimal("0.06192661"),  # 78,3 m²
    "A-201": Decimal("0.04943056"),
    "A-202": Decimal("0.06192661"),
    "A-301": Decimal("0.04943056"),
    "A-302": Decimal("0.06192661"),
    "A-401": Decimal("0.08296425"),  # 104,9 m²
    "A-402": Decimal("0.08296425"),
    "B-101": Decimal("0.04943056"),
    "B-102": Decimal("0.06192661"),
    "B-201": Decimal("0.04943056"),
    "B-202": Decimal("0.06192660"),
    "B-301": Decimal("0.04943056"),
    "B-302": Decimal("0.06192660"),
    "B-401": Decimal("0.08296425"),
    "B-402": Decimal("0.08296425"),
}

# Grupo de prorrateo de la torre B, para gastos extraordinarios que solo la afectan.
PRORRATEOS_TORRE_B = normalizar_prorrateos({u: p for u, p in PRORRATEOS.items() if u[0] == "B"})

# Gastos ordinarios de un mes, por categoría legal (sección 3).
GASTOS_ORDINARIOS_CLP: dict[str, int] = {
    "administracion": 280_000 + 1_150_000,  # honorarios del administrador + conserjería
    "mantencion": 2 * 95_000 + 220_000,  # ascensores de ambas torres + aseo
    "reparacion": 0,
    "uso_consumo": 87_430 + 41_290,  # electricidad y agua de espacios comunes
}
GASTO_ORDINARIO_CLP = sum(GASTOS_ORDINARIOS_CLP.values())  # 1.968.720
