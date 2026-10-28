{
  lib,
  stdenv,
  fetchurl,
  autoPatchelfHook,
  makeWrapper,
  patchelf,
  openssl,
  libsecret,
  release,
}:
let
  # Newer patchelf versions corrupt the Node SEA executable's embedded notes.
  sea_patchelf = patchelf.overrideAttrs {
    version = "0.15.2";
    src = fetchurl {
      url = "https://github.com/NixOS/patchelf/releases/download/0.15.2/patchelf-0.15.2.tar.bz2";
      hash = "sha256-F3RfVkFZyOIo/EEtplogSLhGxLa0Igt3y/IkFuAvLXw=";
    };
    doCheck = false;
  };
in
stdenv.mkDerivation {
  pname = "t3-cli";
  inherit (release) version;
  src = fetchurl { inherit (release.cliAssets.${stdenv.hostPlatform.system}) url hash; };
  nativeBuildInputs = [
    autoPatchelfHook
    makeWrapper
  ];
  buildInputs = [
    stdenv.cc.cc.lib
    openssl
    libsecret
  ];
  dontBuild = true;
  dontStrip = true;
  dontPatchELF = true;
  dontAutoPatchelf = true;
  preFixup = ''
    autoPatchelf "$out/lib/t3/node_modules" "$out/lib/t3/resource-monitor"
    ${sea_patchelf}/bin/patchelf \
      --set-interpreter ${stdenv.cc.bintools.dynamicLinker} \
      --set-rpath ${
        lib.makeLibraryPath [
          stdenv.cc.cc.lib
          openssl
        ]
      } \
      "$out/lib/t3/t3"
  '';
  installPhase = ''
    runHook preInstall
    mkdir -p "$out/lib/t3" "$out/bin"
    cp -r . "$out/lib/t3/"
    makeWrapper "$out/lib/t3/t3" "$out/bin/t3"
    runHook postInstall
  '';
  meta = {
    description = "T3 Code headless CLI and server";
    homepage = "https://github.com/pingdotgg/t3code";
    license = lib.licenses.mit;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "t3";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
