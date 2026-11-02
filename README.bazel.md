# AMD64 management-common with Bazel

This build compiles this checkout's CVL and translib Go code and generates its
YANG bindings, validation schemas, and install trees. It targets native AMD64
Debian Trixie with Bazel 8.5.1, Go 1.25.9, the shared SONiC GCC toolchain and
Python 3.13. It does not generate Debian packages.

| Consumer interface | Output |
| --- | --- |
| `//cvl`, `//translib`, `//translib/ocbinds` | Source-owned Go library providers, including generated bindings |
| `//dist:runtime` | Reproducible TAR: `/usr/models/yang`, `/usr/sbin/schema`, `/usr/sbin/cvl_cfg.json` |
| `//dist:codegen` | Reproducible TAR of prepared YANG, generated Go bindings, and tree/HTML documentation for build consumers |
| `//translib/ocbinds:generated_bindings` | Generated `ocbinds.go`, outside the source tree |

The runtime and code-generation TAR tests compare all installed files against
the existing `debian/*.install` contracts, including their bytes and archive
metadata. All payloads are root-owned with fixed timestamps and normalized
permissions. Downstream management-framework and gNMI should depend on these
owner targets and use the runtime TAR in their container composition.

## Build and test

After the OpenConfig linter registration
[registry PR #163](https://github.com/securely1g/sonic-bazel-registry/pull/163)
lands, the maintained registry configured in `.bazelrc` supplies every module:

```sh
bazel build //cvl //translib //dist:runtime //dist:codegen
bazel test //cvl:cvl_test //translib:translib_test //translib/db:db_test \
  //translib/cs:cs_test //translib/path:path_test //translib/platform:platform_test \
  //translib/internal/apis:apis_test //translib/ocbinds:ocbinds_test \
  //translib/transformer:transformer_test \
  //dist:runtime_test //dist:codegen_contract_test //dist:schema_lint_test
bazel test --config=xfmr //translib/transformer:transformer_model_test
```

During review, CI uses a temporary copy of `.bazelrc` with its one SONiC registry
endpoint replaced by reviewed commit `072b114baeced168815e350d496f512d98760562`.
Normal committed defaults stay on `main`. This source PR remains Draft until
the needed registration is published and temporary CI selection is removed.

`--config=xfmr` selects the existing transformer's `xfmrtest` Go tags and
`INCLUDE_TEST_MODELS=y` schema inputs together. Default builds do not contain
these test models. The default transformer suite uses the existing `testapp`
tests. Experimental prune tag variants are outside this initial configuration.

Tests start private Redis instances with isolated sockets, ports, data and
configuration. The declared Redis and libyang runtime uses its matching Trixie
loader; tests never stop or modify a worker's Redis service. Existing CVL
assertions run against the same generated YIN and JSON fixtures used by Make.
The other Redis suites reuse `tools/test/dbinit.py` and `platform.json`.

## Sources and locks

Model import policy comes from `models/yang/sonic/import.mk`. The shared
`sonic-yang-models` owner builds its wheel; management-common consumes its CVL
models and applies the existing `import_yang.py` transformations. The existing
patched ygot generator produces Go bindings, and the existing owner pyang tools
produce lint results and documentation. No action clones dependencies or
mutates `vendor`, `go.mod`, or a generated source file in the checkout.

Go inputs come from `go.mod`/`go.sum`, with the existing vendor patch set applied
inside isolated external repositories. Bazel's shared Go dependency graph also
contains the rules_go tool dependencies; it selects `golang.org/x/text` 0.40.0
over the source module's 0.39.0 minimum. Source `go.mod` is unchanged. The generated
module resolution and test artifacts record the actual selected graph.

Python tool dependencies are pinned with hashes in `requirements_lock.txt`.
`tools/test/apt.lock.json` freezes the AMD64 Redis 8.0.2 test runtime and its
40-package dependency closure by source URL and SHA256. These external Debian
packages are imported, not produced. To refresh the test lock, resolve only
`mgmt_test_deps` through the selected rules_distroless `apt.install` using the
same immutable Trixie snapshots, export that set's generated lock content, and
rerun all private-Redis suites. Do not replace it with live host packages.

`MODULE.bazel.lock` is generated, ignored, and retained as CI evidence. Bazel's
local action and repository caches can be reused; no clean is needed between
edits. CI starts from a source checkout without generated files and records
the selected inputs, exact TAR hashes, native architecture, commit parents,
test logs, and schema-edit timings in its downloadable artifact.

Run `python3 tools/bazel/check_incremental.py` to measure a normal build, a
no-op, a schema-node edit, and restoration. It verifies that the runtime TAR,
code-generation TAR and Go bindings change after the edit and return to their
original SHA256 values after restoration. Source bytes are restored even when
validation fails. `BAZEL_COMMAND` and `BAZEL_BUILD_FLAGS` accept local cache
configuration; their use does not change the checked-in build contract.
