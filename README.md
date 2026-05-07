# Adi v2 tool import fixes

Uruchom z roota repozytorium `D:\Adi`:

```powershell
py .\apply_v2_tool_import_fixes.py
```

Potem sprawdź:

```powershell
py -m pytest -q
```

Commit:

```powershell
git add .
git commit -m "refactor(tools): move scripts into v2 tool layout"
git push
```

Ten skrypt poprawia importy po przeniesieniu narzędzi do:

- `tools/sutra/`
- `tools/agni/`
- `tools/indra/`

oraz poprawia repo-root w przeniesionych skryptach Sutry.
