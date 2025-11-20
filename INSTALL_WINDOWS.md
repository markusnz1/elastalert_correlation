# Quick Installation Guide for ElastAlert2 CorrelationRule

If you're seeing: `No module named 'elastalert_modules'`

## Fix for Virtual Environment Users (Windows)

If you installed ElastAlert2 in a virtual environment (`.venv`), here's the correct location:

```cmd
REM Activate your venv
.venv\Scripts\activate

REM Find your site-packages directory
python -c "import site; print(site.getsitepackages()[0])"
REM Example output: C:\path\to\.venv\Lib\site-packages

REM Copy elastalert_modules to site-packages ROOT (not inside elastalert folder!)
xcopy /E /I elastalert_correlation\elastalert_modules "C:\path\to\.venv\Lib\site-packages\elastalert_modules"

REM Verify the structure
dir "C:\path\to\.venv\Lib\site-packages\elastalert_modules"
REM Should show: __init__.py and custom_rule_types.py

REM Test import
python -c "import elastalert_modules.custom_rule_types; print('Module found!')"
```

## Correct Structure

```
.venv\Lib\site-packages\
├── elastalert\                  # ElastAlert2 package (already there)
│   ├── __init__.py
│   ├── elastalert.py
│   └── ...
└── elastalert_modules\          # Your custom module (add this as sibling)
    ├── __init__.py
    └── custom_rule_types.py
```

## Wrong Structure (Common Mistake)

```
.venv\Lib\site-packages\
└── elastalert\                  # ElastAlert2 package
    ├── elastalert_modules\      # ❌ WRONG - inside elastalert package
    │   └── ...
    └── ...
```

## Alternative: Use Working Directory

Instead of installing in site-packages, you can place the module in your working directory:

```cmd
REM Copy to where you run ElastAlert2 from
cd C:\path\to\your\elastalert\workspace
xcopy /E /I C:\path\to\elastalert_correlation\elastalert_modules elastalert_modules

REM Your directory should look like:
REM C:\path\to\your\elastalert\workspace\
REM ├── config.yaml
REM ├── rules\
REM └── elastalert_modules\
```

## Rule Configuration

In your rule YAML file:

```yaml
type: "elastalert_modules.custom_rule_types.CorrelationRule"
```

Note: The quotes around the type are required!

## Full Documentation

See README.md for complete documentation and examples.
