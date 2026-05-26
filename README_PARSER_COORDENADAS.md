# Parser por coordenadas X/Y

Esta versión cambia la lectura de los PDFs ALARDE.

## Qué corrige

El PDF no es texto lineal: es una tabla visual. Cuando una celda ocupa varias líneas, el texto puede quedar cortado o mezclado.

Ahora el parser:
- detecta cada expediente por su posición en la columna Nº Proced.;
- reconstruye cada fila hasta el siguiente expediente;
- lee cada campo por coordenadas:
  - Procedimiento;
  - F. Aceptación;
  - Materia;
  - Fase Procesal;
  - Último trámite;
  - Fecha Últ. Trámite;
- conserva textos multilínea dentro de cada campo.

## Ejemplos que corrige

- `Ejecución de títulos` + `judiciales`
- `Condiciones generales de la` + `contratación`
- `Inicio/Demand` + `a`
- últimos trámites en varias líneas.

## Archivos principales a sustituir

- parser_pdf.py
- version.py

Puedes subir el paquete completo si quieres mantener consistencia.
