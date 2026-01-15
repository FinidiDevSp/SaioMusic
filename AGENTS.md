# AGENTS

Guia rapida para trabajar en SaioMusic.

## Objetivo del proyecto
Aplicacion de Windows para reproduccion musical con enfoque en productividad, coleccion y flujo rapido.

## Stack y alcance
- Lenguaje: Python 3.11+
- Entorno: Windows
- Estado: base de repo, UI pendiente de definir (framework a decidir)

## Puesta en marcha (dev)
```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
pre-commit install
```

## Comandos habituales
```bash
# tests
py -m pytest -q

# lint y formato
ruff check src tests
black --check src tests
mypy src
```

## Convenciones
- Commits: Conventional Commits (requerido por Release Please)
- Ramas: `main` es estable; usar feature branches y PRs
- Calidad: no mergear sin pasar CI

## Flujo obligatorio (cuando se crea o modifica un archivo)
1. Crear una rama para el cambio.
2. Hacer los cambios.
3. Commit local siguiendo Conventional Commits.
4. Empujar la rama al remoto.
5. No usar PR: los commits deben quedar en remoto directamente.

## CI y automatizacion
Workflows actuales:
- `.github/workflows/ci.yml` (lint + tests)
- `.github/workflows/release-please.yml` (releases automaticas)

Pendiente de considerar:
- Dependabot para actualizacion de dependencias
- CodeQL para analisis de seguridad
- Matriz de CI (Windows/macOS/Linux) si el runtime lo requiere

## Documentacion y soporte
- `README.md` describe vision, instalacion y estructura
- `CONTRIBUTING.md` define reglas de contribucion
