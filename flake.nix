{
  description = "T3 Code desktop, headless CLI and NixOS runtime compatibility";
  nixConfig = {
    extra-substituters = [ "https://t3-code-nix-flake.cachix.org" ];
    extra-trusted-public-keys = [
      "t3-code-nix-flake.cachix.org-1:nyr+c/F8Xmvnook2Yayw4DV7fGNKZXIIZQ/UwMYz6yg="
    ];
  };
  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";

  outputs =
    { self, nixpkgs }:
    let
      systems = [
        "x86_64-linux"
        "aarch64-linux"
      ];
      for_all_systems = nixpkgs.lib.genAttrs systems;
      releases = builtins.fromJSON (builtins.readFile ./releases.json);
      make_cli = pkgs: channel: pkgs.callPackage ./nix/cli.nix { release = releases.${channel}; };
      cli_smoke =
        pkgs: package:
        pkgs.runCommand "${package.name}-smoke"
          {
            nativeBuildInputs = [
              pkgs.python3
              pkgs.git
              pkgs.openssh
            ];
          }
          ''
            python ${./scripts/cli-smoke.py} ${package}/bin/t3
            touch $out
          '';
      make_package =
        pkgs: channel:
        pkgs.callPackage ./nix/package.nix {
          release = releases.${channel};
        };
    in
    {
      packages = for_all_systems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          t3code = make_package pkgs "stable";
          t3code-nightly = make_package pkgs "nightly";
          t3-cli = make_cli pkgs "stable";
          t3-cli-nightly = make_cli pkgs "nightly";
          default = self.packages.${system}.t3code;
        }
      );
      nixosModules.runtime-compat = import ./nix/runtime-compat.nix;
      overlays.default = final: _prev: {
        t3-cli = make_cli final "stable";
        t3-cli-nightly = make_cli final "nightly";
        t3code = make_package final "stable";
        t3code-nightly = make_package final "nightly";
      };
      checks = for_all_systems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          stable = self.packages.${system}.t3code;
          nightly = self.packages.${system}.t3code-nightly;
          cli-stable = self.packages.${system}.t3-cli;
          cli-nightly = self.packages.${system}.t3-cli-nightly;
          cli-stable-smoke = cli_smoke pkgs self.packages.${system}.t3-cli;
          cli-nightly-smoke = cli_smoke pkgs self.packages.${system}.t3-cli-nightly;
          updater = pkgs.runCommand "updater-tests" { nativeBuildInputs = [ pkgs.python3 ]; } ''
            cd ${self}
            PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
            touch $out
          '';
        }
      );
      formatter = for_all_systems (system: nixpkgs.legacyPackages.${system}.nixfmt);
      devShells = for_all_systems (
        system:
        let
          pkgs = nixpkgs.legacyPackages.${system};
        in
        {
          default = pkgs.mkShell {
            packages = with pkgs; [
              python3
              nixfmt
              statix
              deadnix
              actionlint
              xvfb-run
            ];
          };
        }
      );
    };
}
