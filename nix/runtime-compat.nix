{ pkgs, ... }:
{
  # Desktop SSH setup and `t3 service install` download unpatched Linux
  # runtimes. Keep those verified upstream binaries runnable on NixOS too.
  programs.nix-ld = {
    enable = true;
    libraries = with pkgs; [
      stdenv.cc.cc.lib
      openssl
      libsecret
    ];
  };
}
