# Arquitectura del Grafo LangGraph - Tiendita IA

```mermaid
---
config:
  flowchart:
    curve: linear
---
graph TD;
	__start__([<p>__start__</p>]):::first
	supervisor(supervisor)
	control(control)
	vendedor(vendedor)
	analista(analista)
	investigador(investigador)
	publicista(publicista)
	tutor_ui(tutor_ui)
	approval_gate(approval_gate<hr/><small><em>__interrupt = before</em></small>)
	__end__([<p>__end__</p>]):::last
	__start__ --> supervisor;
	analista -.-> __end__;
	analista -.-> supervisor;
	approval_gate -.-> __end__;
	approval_gate -.-> supervisor;
	control -.-> __end__;
	control -.-> approval_gate;
	control -.-> supervisor;
	investigador -.-> __end__;
	investigador -.-> supervisor;
	publicista -.-> __end__;
	publicista -.-> approval_gate;
	publicista -.-> supervisor;
	supervisor -.-> __end__;
	supervisor -.-> analista;
	supervisor -.-> control;
	supervisor -.-> investigador;
	supervisor -.-> publicista;
	supervisor -.-> tutor_ui;
	supervisor -.-> vendedor;
	tutor_ui -.-> __end__;
	tutor_ui -.-> supervisor;
	vendedor -.-> __end__;
	vendedor -.-> approval_gate;
	vendedor -.-> supervisor;
	classDef default fill:#f2f0ff,line-height:1.2
	classDef first fill-opacity:0
	classDef last fill:#bfb6fc

```
