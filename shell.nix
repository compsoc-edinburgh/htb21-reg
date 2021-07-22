let
  mach-nix = import (builtins.fetchGit {
    url = "https://github.com/DavHau/mach-nix/";
    ref = "refs/tags/3.3.0";
  }) {};
  newWerkzeug = (mach-nix.buildPythonPackage {
    src = (builtins.fetchGit {
      url = "https://github.com/pallets/werkzeug/";
      ref = "refs/tags/2.0.1";
    });
  }).overrideAttrs (oldAttrs: rec {
    postPatch = ''
      substituteInPlace src/werkzeug/_reloader.py \
        --replace "rv = [sys.executable]" "return sys.argv"
    '';
  });
  pkgs = import <nixpkgs> {};
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    (mach-nix.mkPython {
      requirements = builtins.readFile ./requirements.txt;
      
      overridesPost = [
        (self: super: {
          werkzeug = newWerkzeug;
        })
      ];
    })
    sqlite
  ];
}
