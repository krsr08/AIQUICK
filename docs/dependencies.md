# Dependency and supplied-asset register

Observed 2026-10-17. Source: local ZIP directory/selected licence entries, Windows CIM/file version metadata, installed `.venv` distribution metadata and `config/requirements.lock`. Full machine-readable entries and licence-file paths are in [dependency-inventory.json](dependency-inventory.json). No supplied archive was installed or fully extracted for this inventory.

## Runtime and hardware

- Windows 11 Home Single Language 10.0.26200; Intel Core i3-1215U, 6 cores / 8 logical processors.
- Physical RAM 25,448,615,936 bytes (about 23.7 GiB); available physical memory at inventory 1,803,348 KiB (about 1.7 GiB), a transient snapshot.
- Intel UHD Graphics reports 1,073,741,824 bytes AdapterRAM; this CIM field does not establish dedicated VRAM or usable model acceleration.
- Project virtual environment Python 3.12.13; installed Chrome 153.0.8010.53; installed Edge 154.0.4258.37.
- Downloads chrome.exe file metadata reports 149.0.7827.115; it is not the installed Chrome binary and was not executed.
- Conservative planning: one browser workflow at a time until measured memory/CPU evidence supports more. No model performance, GPU capability or concurrent-worker density benchmark was run. Close competing workloads before inference evaluation; no model sizing guarantee.
- Docker readiness remains unresolved after the implementation owner's bounded investigation reported a hung info query. This inventory did not rerun Docker. Ollama model availability and a licence-approved model shortlist are not established here.

## Direct dependency rationale

| Package | Use / reason |
|---|---|
| FastAPI 0.143.3 | Typed control-plane and policy HTTP APIs; blueprint backend choice |
| Pydantic 2.14.1 | Strict domain/input/output contracts and plan validation; blueprint schema choice |
| Uvicorn 0.54.0 | ASGI server for explicitly bound local development services |
| Selenium 4.51.0 | Real browser WebDriver execution behind controlled dispatcher; registry package used instead of unversioned supplied source tree |
| httpx 0.28.1 | Bounded HTTP calls between service processes and integration-test client |
| pytest 9.1.1 | Repeatable unit/integration/negative browser acceptance tests |
| bandit 1.9.4 | Python static security analysis; findings need inspection |
| pip-audit 2.10.1 | Installed dependency known-vulnerability audit |
| cyclonedx-bom 7.5.0 | Generate machine-readable dependency SBOM |
| pip 26.2.1 | Reproducible environment installation tooling |

The remaining pins support these runtimes/tools (HTTP/TLS, async I/O, validation, schema formats, reporting and SBOM/licence parsing). Keep build/audit tools out of production images when packaging. The lock fixes versions but lacks artifact hashes; hash-locked/offline reproducible installation remains follow-up work.

## Observed audit and licence limitations

The existing actual pip-audit JSON contains 81 dependency records and 0 reported known vulnerabilities. SHA-256 of that result: `70fd8b70d2320ee455c9e8272244e523699a0cc94eae385432b741b6081ca621`. This describes that scan, not absence of all vulnerabilities or licence approval. The audit was run by the implementation owner, not rerun by the documentation task.

Metadata inspection is a licence inventory, not completed legal approval. Preserve required licence/NOTICE files on redistribution. Review MPL-2.0 components (certifi and fqdn), PSF terms, packageurl-python's missing licence file in distribution, vendored dependencies, and lxml's bundled components before redistribution. The inspected lxml LICENSES.txt explicitly describes additional component terms including LGPL 2.1 iconv and other exceptions; a BSD top-level metadata label is not sufficient clearance. No supplied Edge EULA acceptance or driver certification is implied.

## Complete installed pin / licence register

All 81 lock pins matched installed versions at inventory. Labels below come from metadata except explicit inspected-text notes.

| Package | Pin / installed | Declared or inspected licence |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| arrow | 1.4.0 | Apache Software License |
| attrs | 26.1.0 | MIT |
| bandit | 1.9.4 | Apache-2.0 |
| boolean-py | 5.0 | BSD-2-Clause |
| cachecontrol | 0.14.4 | Apache-2.0 |
| certifi | 2026.7.22 | MPL-2.0 |
| cffi | 2.1.1 | MIT-0 |
| chardet | 7.6.0 | 0BSD |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| colorama | 0.4.6 | BSD-3-Clause (installed LICENSE inspected) |
| cyclonedx-bom | 7.5.0 | Apache-2.0 |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 |
| defusedxml | 0.7.1 | PSFL |
| fastapi | 0.143.3 | MIT |
| filelock | 4.2.0 | MIT |
| fqdn | 1.6.0 | MPL-2.0 |
| h11 | 0.16.0 | MIT |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| idna | 3.20 | BSD-3-Clause |
| iniconfig | 2.3.1 | MIT |
| isoduration | 20.11.0 | ISC (installed LICENSE inspected; metadata UNKNOWN) |
| jsonpointer | 3.2.1 | BSD-3-Clause (installed LICENSE inspected) |
| jsonschema | 4.26.0 | MIT |
| jsonschema-specifications | 2025.9.1 | MIT |
| lark | 1.3.1 | MIT |
| license-expression | 30.4.4 | Apache-2.0 |
| lxml | 6.1.3 | BSD-3-Clause |
| markdown-it-py | 4.2.0 | MIT License |
| mdurl | 0.1.2 | MIT License |
| msgpack | 1.2.3 | Apache-2.0 |
| opentelemetry-api | 1.45.1 | Apache-2.0 |
| outcome | 1.3.0.post0 | MIT OR Apache-2.0 |
| packageurl-python | 0.17.6 | MIT |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pip | 26.2.1 | MIT |
| pip-api | 0.0.35 | Apache-2.0 (metadata contains full licence text) |
| pip-audit | 2.10.1 | Apache Software License |
| pip-requirements-parser | 32.0.1 | MIT |
| platformdirs | 4.13.3 | MIT |
| pluggy | 1.7.0 | MIT |
| py-serializable | 2.1.0 | Apache-2.0 |
| pycparser | 3.11 | BSD-3-Clause |
| pydantic | 2.14.1 | MIT |
| pydantic-core | 2.50.1 | MIT |
| pygments | 2.21.0 | BSD-2-Clause |
| pyparsing | 3.3.3 | MIT |
| pysocks | 1.7.1 | BSD-3-Clause (installed LICENSE inspected) |
| pytest | 9.1.1 | MIT |
| python-dateutil | 2.9.0.post0 | Apache-2.0 and BSD-3-Clause (see installed LICENSE) |
| pyyaml | 6.0.3 | MIT |
| referencing | 0.37.0 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| rfc3339-validator | 0.1.4 | MIT license |
| rfc3986-validator | 0.1.1 | MIT license |
| rfc3987-syntax | 1.1.0 | MIT |
| rich | 15.0.0 | MIT |
| rpds-py | 2026.9.1 | MIT |
| selenium | 4.51.0 | Apache-2.0 |
| six | 1.17.0 | MIT |
| sniffio | 1.3.1 | MIT OR Apache-2.0 |
| sortedcontainers | 2.4.0 | Apache 2.0 |
| starlette | 1.8.0 | BSD-3-Clause |
| stevedore | 5.9.1 | Apache-2.0 |
| tomli | 2.5.0 | MIT |
| tomli-w | 1.2.0 | MIT License |
| trio | 0.34.0 | MIT OR Apache-2.0 |
| trio-websocket | 0.12.2 | MIT License |
| typing-extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| tzdata | 2026.5 | Apache-2.0 |
| uri-template | 1.3.0 | MIT License |
| urllib3 | 2.8.0 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| webcolors | 25.10.0 | BSD-3-Clause |
| websocket-client | 1.9.2 | Apache-2.0 |
| wsproto | 1.3.2 | MIT |

## Supplied assets (not reused)

| Asset | Bytes | SHA-256 | Finding |
|---|---:|---|---|
| chrome.exe | 4205720 | `69c8c7e2d950845df00c1e9f7c024e143c9efdc43401c6fb5009cad89bbf4ef9` | File version inspected only; not executed |
| edgedriver_win32.zip | 9812426 | `9ab38537c14f691b3d728e112fa9d76044d3fd81ea24401367eca1cff31aa2a3` | 5 entries; msedgedriver.exe; Microsoft Edge WebDriver EULA and Chromium/Microsoft LICENSE present; version/compatibility not executed |
| edgedriver_win64.zip | 11715108 | `00dd7fbc6fc4bd68e6e86badbe76e6570513414085f476e73d3787ba3410d562` | 5 entries; msedgedriver.exe; Microsoft Edge WebDriver EULA and Chromium/Microsoft LICENSE present; version/compatibility not executed |
| geckodriver-v0.37.1-win32.zip | 1698255 | `7b4bfd914e24a843db2dc38ba515086d28828601aaf443e9d2664918e343fb99` | Single geckodriver.exe entry; no licence file in ZIP; filename version unverified; Firefox out of scope |
| geckodriver-v0.37.1-win64.zip | 1780114 | `dfed9315abe8d2fbc1b6161a2ee8002452e79cf05ee92fdc653a4e26bc35edd8` | Single geckodriver.exe entry; no licence file in ZIP; filename version unverified; Firefox out of scope |
| selenium-trunk.zip | 46030693 | `c15d5fbc7b288d2bb2fbc209e6b81ce9c82986b1c95b5ef54225e7e01e06cb86` | 6,121 entries; Apache-2.0 LICENSE and NOTICE; unversioned trunk source not reused |

No Edge/Gecko browser test was run by this inventory. Actual Chrome execution and driver version belong in the implementation verification report. ZIP hashes establish the inspected bytes, not upstream authenticity or malware clearance.
