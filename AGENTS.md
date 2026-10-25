# Agent instructions — Construction Carbon Research

This repository contains a research-stage carbon accounting web app for construction.

- Work on a task branch and open a PR. Never push directly to a protected branch.
- Keep the dependency direction `apps → workflows → codes → core`; keep engineering and carbon rules out of UI and routes.
- Every dimensioned value crossing a package boundary must carry a unit. Keep calculation traces and source/version references.
- Route UI and report copy through Thai and English translation catalogs.
- Do not copy standards or source BOQ PDFs into this public repository. The Kiakkai sample is a disclosed, partial derived example.
- Do not claim that inventory reductions are issued carbon credits. Human LCA/engineering review and TGO verification are required for real-world use.
- Do not access production secrets, databases, or customer data.
- Run relevant Ruff, mypy, pytest and frontend build checks before opening a PR.
- Identify AI-assisted commits with a co-author trailer.
