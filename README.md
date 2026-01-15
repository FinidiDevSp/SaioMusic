# SaioMusic

Reproductor de musica personalizable enfocado en productividad, coleccion y flujo rapido.

![CI](https://github.com/FinidiDevSp/SaioMusic/actions/workflows/ci.yml/badge.svg?branch=master)
![Release](https://github.com/FinidiDevSp/SaioMusic/actions/workflows/release-please.yml/badge.svg?branch=master)

## Vision

Un reproductor de musica para uso diario con:
- atajos rapidos y workflows claros
- organizacion flexible por etiquetas y colecciones
- integracion futura con biblioteca local y servicios

## Estado

Proyecto en fase de inicio. Esta base prepara el repo para desarrollo serio.

## Requisitos

- Python 3.11+
- Git

## Instalacion (dev)

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
pre-commit install
```

## Uso (por ahora)

```bash
saiomusic
```

## Estructura

```
src/saio_music/    codigo fuente
tests/             pruebas
.vscode/           configuracion para debug
.github/workflows/ automatizacion CI/release
```

## Calidad

- `ruff` para lint
- `black` para formato
- `mypy` para tipado
- `pytest` para pruebas

## Releases

Automatizadas con Release Please. Los cambios se agrupan via Conventional Commits.

## Licencia

MIT
