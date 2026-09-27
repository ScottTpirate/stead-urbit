# Phase 1 evidence builder: independent review, 2026-09-25

Disposition: no blocking finding remains in the two requested fixes at the exact source hashes below. This is an independent source and regression-test review by the editor-tool review agent, separate from the builder author and root integrator. It does not establish native Phase 1 acceptance.

| Reviewed file | SHA-256 |
| --- | --- |
| `scripts/urbit/build_phase1_evidence.py` | `de7492a0c2d2a124cf87062f4e26131ab9c25c9dde3194b1a2b7556e7efe2387` |
| `tests/urbit/test_phase1_evidence_builder.py` | `ea7f9640824e65bca442e95c7b306784285d3d7defa8aa5453f331183ba4d808` |

The integrator reports these files committed in `b9765bf60d1a560ee453b3ee4c721714f3232991`. Both file hashes were independently read and matched before this review record was written. Origin fetch and push URLs were verified as `https://github.com/ScottTpirate/stead-urbit.git`; upstream remains read-only.

1. **Output-directory redirection finding resolved.** `main` holds a parent directory descriptor obtained through `execution_policy.directory_fd`, whose component walk uses `O_DIRECTORY | O_NOFOLLOW`. It rejects existing output names, retains the descriptor during derivation, and rechecks parent device/inode before creating the output directory. Directory creation and child/file opens use directory-relative descriptors; output files are exclusive and no-follow. The reviewed regressions cover an initial parent symlink, parent replacement during derivation, and output-directory replacement with a symlink after creation. These changes address the original pathname-following race without rewriting retained inputs.

2. **Export metadata binding finding resolved.** `export_records` derives the maximum response byte count from retained native raw strings and requires the claimed value to match. It reconstructs the bounded commit/tree/blob graph and object order, recomputes Git object IDs, and checks the native response routes, scope, contents, and recorded file inventory. The original transport run ID and export ordinal determine the required Git working directory. Every materialization, HEAD, ref, fsck, ls-tree, and cat-file command must match the expected argv, order, return code, and output; an embedded `fsck` suffix in an unrelated command is rejected. The reviewed twelve tampering subcases exercise those bindings and preserve the original capture. This replay performs no Git or native process execution.

The builder author reports **19 host tests passed in 0.257 seconds**, including the twelve export tampering subcases and directory replacement controls. The root integrator separately reports **403 integrated host tests passed in 21.907 seconds**. This reviewer inspected the regression source but did not rerun either suite in this final pass. The historical replay check retains its actual result: 148 QA rows, 145 passed and three typed skips, followed by the historical round-trip failure; it does not turn that failed run into acceptance.

No native work was executed for this review. Final Phase 1 qualification still requires the actual complete lanes, retained failures and exact source/input/guard bindings to satisfy the qualification gate. This bounded disposition covers the two fixes above and is not deployment approval or a general certification of the repository.
