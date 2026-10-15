# Security

## Reporting a vulnerability

Report security issues **privately** through GitHub's vulnerability reporting at
<https://github.com/DailybotHQ/slicra/security>, not in a public issue. Include the Slicra
version, the command or API call, and (if possible) a synthetic input that reproduces it.

## Security posture

Slicra is an offline library and CLI. It has **no network access, no authentication, no
secrets, no telemetry and no server**. Its attack surface is the untrusted input it reads and the
files it writes:

| Surface | Threat | Mitigation (where) |
| --- | --- | --- |
| YAML/JSON config, regions files, templates | Code execution via YAML tags | `yaml.safe_load` only (`config.py::_safe_yaml`, `detectors/manual.py`); unknown keys rejected (`StrictModel`) |
| Template references | Path traversal to arbitrary files | Built-in names must match `^[a-z0-9][a-z0-9-]*$`; file templates must be existing `.yaml` files; no template chains (`config.py::_read_template`) |
| Image files | Decompression bombs, corrupt files | `input.max_pixels` (default 150 M px) and Pillow's bomb guard mapped to `ImageLoadError` (`imageio.py`) |
| Output naming | Writing outside the output directory, clobbering files | Allowed fields only, sanitized names, resolved-parent check, duplicate check, pre-write conflict check, `--overwrite` opt-in, never the input path (`export.py`, `pipeline.py`) |
| Batch mode | Re-processing its own outputs | Only direct children of the input folder; output folder excluded; output must differ from input (`imageio.iter_images`, `pipeline.extract_batch`) |
| Source images | Accidental modification | Opened read-only; all edits on copies |
| Agent Skill | Data exfiltration by an agent | The skill only runs the local CLI and instructs agents not to upload images |

SVG is not supported, so there is no external-reference or script surface from vector files.

## Supply chain

- Runtime dependencies: Pillow, Pydantic, PyYAML, Typer; optional NumPy + opencv-python-headless.
  Ranges are in `pyproject.toml`; review upgrades with `/lib-upgrade` (batched, gated).
- Vendored agent skills under `.agents/skills/deepworkplan/` (v7.8.1) and
  `.agents/skills/ai-diff-reviewer/` (v3.3.14) are pinned; `skills-lock.json` records their
  content hashes. Upgrade them only through `/dwp-upgrade` or the pinned install commands.
- Publishing to PyPI is manual and requires maintainer approval; CI has no publishing secrets.

## Rules for agents and contributors

- Never commit secrets, tokens, `.env` files or private images. The repository needs none.
- Never add photographs of real people to tests, examples or docs; use synthetic fixtures.
  Local real-image regression runs read from `SLICRA_SAMPLES`, outside the repository.
- Never add network calls, telemetry, `pickle`, `eval`/`exec` or `shell=True` to `src/slicra/`.
- Treat a change to any mitigation in the table above as security-relevant: it needs a test and
  a security note in the PR description.
