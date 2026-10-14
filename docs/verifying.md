# Verifying a release

Releases from `py-v0.1.1` on are signed in two ways, with no key to manage: the signatures are tied
to the GitHub Actions workflow that built the files, through Sigstore.

1. **Build provenance.** GitHub stores a signed statement of which workflow run, commit and tag
   produced each file.
2. **A cosign signature** over `checksums.txt`, shipped as `checksums.txt.sigstore.json`.

## Check a file against its provenance

```sh
gh attestation verify gascoigne-0.1.1-py3-none-any.whl --repo gascoigne-ai/gascoigne-sdk
```

It prints the workflow, commit and tag the file came from, and fails if the file was changed or was
not built by this repository's release workflow.

## Check the checksums with cosign

```sh
cosign verify-blob checksums.txt \
  --bundle checksums.txt.sigstore.json \
  --certificate-identity-regexp '^https://github.com/gascoigne-ai/gascoigne-sdk/\.github/workflows/release\.yml@refs/tags/' \
  --certificate-oidc-issuer https://token.actions.githubusercontent.com
sha256sum --check checksums.txt
```

The first command proves `checksums.txt` came from the release workflow; the second proves your files
match it.

## What is not signed

- Releases before `py-v0.1.1` have checksums only.
- The packages on GitHub Packages (npm, Maven, NuGet) are published by the same workflow, but the
  registries do not carry these signatures. Verify the release files, or compare checksums.
- No GPG signature for Maven Central and no NuGet package signature yet: both need a certificate
  that has to be bought or issued. They become relevant when publishing to Maven Central and
  nuget.org.
- PyPI, npm and crates.io: when published there, use the registry's own provenance (PyPI trusted
  publishing attestations, `npm publish --provenance`).
