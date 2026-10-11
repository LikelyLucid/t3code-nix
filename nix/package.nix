{
  lib,
  stdenv,
  fetchurl,
  appimageTools,
  release,
}:
let
  pname = "t3code";
  inherit (release) version;
  src = fetchurl {
    inherit (release.assets.${stdenv.hostPlatform.system}) url hash;
  };
  appimage_contents = appimageTools.extract { inherit pname version src; };
in
appimageTools.wrapType2 {
  inherit pname version src;
  extraInstallCommands = ''
    install -Dm644 ${appimage_contents}/t3code.desktop $out/share/applications/t3code.desktop
    substituteInPlace $out/share/applications/t3code.desktop \
      --replace-fail "Exec=AppRun" "Exec=t3code"
    cp -r ${appimage_contents}/usr/share/icons $out/share
  '';
  meta = {
    description = "T3 Code desktop coding agent";
    homepage = "https://github.com/pingdotgg/t3code";
    license = lib.licenses.mit;
    platforms = [
      "x86_64-linux"
      "aarch64-linux"
    ];
    mainProgram = "t3code";
    sourceProvenance = [ lib.sourceTypes.binaryNativeCode ];
  };
}
