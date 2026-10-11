# T3 Code for Nix

Standalone packaging of the official [T3 Code](https://github.com/pingdotgg/t3code)
AppImages. Supports **x86_64-linux** and **aarch64-linux**.

```sh
# Normal release (also the default package)
nix run github:LikelyLucid/t3code-nix#t3code
# Upstream nightly, excluding preview builds
nix run github:LikelyLucid/t3code-nix#t3code-nightly
```

Add to a NixOS or Home Manager flake:

```nix
inputs.t3code.url = "github:LikelyLucid/t3code-nix";
inputs.t3code.inputs.nixpkgs.follows = "nixpkgs";
```

Then install one channel:

```nix
home.packages = [ inputs.t3code.packages.${pkgs.stdenv.hostPlatform.system}.t3code-nightly ];
```

An overlay is also available as `inputs.t3code.overlays.default`. Both variants
install `t3code` and the same desktop entry; choose one per profile.
Refresh your consumer's lock with `nix flake update t3code` to adopt updates.

## Automated updates and checks

Every six hours (and on manual dispatch), CI checks GitHub's stable release and
published nightlies. It pins both AppImages by SHA-256 and checks upstream
checksums when the upstream manifest includes the asset. Upstream's current
`SHA256SUMS` only covers CLI archives; AppImage hashes are computed locally.
Missing assets, unexpected URLs, download failures, and checksum mismatches
abort without replacing the existing manifest. Both architectures must build
and pass checks plus headless Electron startup before the bot commits pins to
`main`. Manual dispatch runs full validation even when pins are unchanged. If `main` changes meanwhile, the update fails rather than publishing
against an untested base; the next scheduled run retries.

Pushes and PRs also check formatting, Statix, deadnix, actionlint, updater tests,
flake evaluation, both package builds and startup on native Linux runners.
Actions are pinned by commit, permissions are scoped, jobs have timeouts, and
PR jobs cannot publish to Cachix. Ubuntu runner jobs allow unprivileged user
namespaces before AppImage startup (required by its Bubblewrap FHS wrapper);
this changes only the disposable runner, not consumer machines. Bot pushes made with `GITHUB_TOKEN` do not
trigger another workflow; the update workflow validates the exact pins first.
Startup tests prove headless application launch, not provider authentication
or full interactive functionality. Scheduled runs can be delayed by GitHub;
GitHub disables schedules on inactive public repos after 60 days.

```sh
nix develop --command bash scripts/check.sh
python3 scripts/update.py
nix build .#t3code .#t3code-nightly
```

## Free binary caches

Nix downloads available dependencies from `cache.nixos.org`. CI additionally
restores/saves its Nix store using GitHub Actions caching. That cache is for CI,
not a public substituter for your workstation.

Public Cachix publishing is enabled when repository variable `CACHIX_CACHE`
and secret `CACHIX_AUTH_TOKEN` are configured. Create/use a **free open-source
cache**, not a paid trial. [Cachix provides 5 GB for open-source projects](https://www.cachix.org/pricing),
with least-recently-used eviction when full. No paid service is required.

```sh
# Once the cache is populated, consumers can use it:
cachix use t3-code-nix-flake
nix run github:LikelyLucid/t3code-nix#t3code
```

The flake advertises the cache URL and key (accept its Nix configuration when
prompted). For declarative NixOS use:

```nix
nix.settings.substituters = [ "https://t3-code-nix-flake.cachix.org" ];
nix.settings.trusted-public-keys = [
  "t3-code-nix-flake.cachix.org-1:nyr+c/F8Xmvnook2Yayw4DV7fGNKZXIIZQ/UwMYz6yg="
];
```
Never add an authentication token to a flake or Nix store file.

[Standard GitHub-hosted runners are free for public repositories](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
This repository uses standard Ubuntu x86_64 and ARM64 runners.

## Scope

This repository contains packaging only, not your NixOS host configuration or
T3 conversation data. Packaging is MIT licensed; the bundled application is
copyright T3 Tools Inc. and distributed under its upstream MIT license.
