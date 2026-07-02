"""Familias de ganchos y CTAs (curadas del banco de Isaac, style/banco-ganchos.md).

El LLM elige la familia y adapta el ___ al tema; la rotación se logra
instruyéndolo a comparar contra los ganchos recientes que ya van en el
CONTEXTO DEL CANAL (notion_reader) y los del mismo día (append_avoid_hooks).
"""

FAMILIAS = {
    "reflexion": {
        "tipos": ["lifestyle", "vlog", "opinion"],
        "ejemplos": [
            "Esto nadie te lo dice, pero todos lo piensan...",
            "¿Qué pasaría si te dijera que ___?",
            "Nadie te ha contado esto de ___...",
        ],
    },
    "principiantes": {
        "tipos": ["howto", "tech"],
        "ejemplos": [
            "Cómo empezar con ___ sin sentirte abrumado",
            "El error que comete todo principiante en ___",
            "Mi flujo de trabajo exacto para ___ (puedes copiarlo)",
            "Las 5 cosas que me hubiera gustado saber antes de empezar ___",
        ],
    },
    "hacks": {
        "tipos": ["howto", "tech"],
        "ejemplos": [
            "3 herramientas que uso a diario para ___",
            "Si siempre olvidas ___, prueba esto",
            "La forma perezosa en la que organizo mi ___ (y funciona)",
        ],
    },
    "instantaneo": {
        "tipos": ["trend", "howto", "lifestyle", "opinion", "tech", "fsd", "vlog"],
        "ejemplos": [
            "Probablemente estás haciendo ___ mal (y ni siquiera te das cuenta)",
            "Por qué tu ___ no está funcionando (y cómo solucionarlo)",
            "Cometí este error durante meses; no hagas lo mismo",
        ],
    },
    "choque_real": {
        "tipos": ["trend", "tech", "fsd"],
        "prioridad": True,  # la que mejor le ha funcionado a Isaac
        "ejemplos": [
            "Vi que [noticia real verificada] y como futuro ingeniero me pregunté...",
            "Puse a [herramienta/IA] a decidir ___. El resultado ofendió a media familia.",
            "[Cifra específica]. Eso es lo que me cuesta/tarda ___.",
        ],
    },
    "vlog": {
        "tipos": ["vlog"],
        "ejemplos": [
            "Abrir con la escena más visual del día SIN explicar; la explicación va en voz en off",
            "Hoy pasé el día [haciendo X]. Esto fue lo que aprendí.",
            "No planeaba grabar esto, pero pasó algo que quiero compartir.",
        ],
    },
}

CTAS = {
    "utilidad": 'El favorito de Isaac: "Guarda esto para cuando [situación específica del tema]" / "Mándale esto al que [situación, con humor]"',
    "pregunta_especifica": 'Pregunta que SOLO quien vio el video puede responder — nunca "¿qué opinas?" suelto',
    "indirecto_seguir": 'NUNCA "sígueme" literal. Implicar continuidad: "Esto lo voy a seguir documentando, se viene la segunda parte"',
    "reflexivo": "Solo para contenido personal: dejar la reflexión sin pedir nada",
    "feedback": '"¿Les gustaría que les cuente más de [tema]?"',
}


def build_ganchos_block(script_type: str) -> str:
    aplicables = {
        name: fam for name, fam in FAMILIAS.items() if script_type in fam["tipos"]
    }
    if not aplicables:
        aplicables = {"instantaneo": FAMILIAS["instantaneo"]}

    lines = ["LIBRERÍA DE GANCHOS — elige UNA familia y adapta el ___ al tema:"]
    for name, fam in aplicables.items():
        tag = " (PRIORIDAD ALTA — la que mejor le funciona a Isaac)" if fam.get("prioridad") else ""
        lines.append(f"- Familia '{name}'{tag}:")
        lines += [f'    · "{e}"' for e in fam["ejemplos"]]

    lines.append(
        "\nREGLAS DE GANCHO: debe poder decirse/leerse en máximo 2-3 segundos. "
        "NUNCA uses la misma familia dos veces seguidas — compara contra los ganchos "
        "recientes del CONTEXTO DEL CANAL y los ya generados hoy, y si la familia se "
        "repite, elige otra."
    )
    lines.append("\nFAMILIAS DE CTA — elige la que corresponda al contenido:")
    lines += [f"- {name}: {desc}" for name, desc in CTAS.items()]
    lines.append(
        'REGLA DE CTA: jamás "sígueme" literal; si es pregunta, específica al contenido.'
    )
    return "\n".join(lines)
