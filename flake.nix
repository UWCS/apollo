{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-parts.url = "github:hercules-ci/flake-parts";
    systems.url = "github:nix-systems/default";
    devenv.url = "github:cachix/devenv";

    poetry2nix.url = "github:nix-community/poetry2nix";
  };

  outputs =
    inputs:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } {
      imports = [ inputs.devenv.flakeModule ];
      systems = import inputs.systems;
      debug = true;
      perSystem =
        { config, pkgs, ... }:
        let
          poetry2nix = inputs.poetry2nix.lib.mkPoetry2Nix { inherit pkgs; };
          projectDir = ./.;
          preferWheels = true;
          overrides = poetry2nix.defaultPoetryOverrides.extend (
            final: prev:
            builtins.mapAttrs (
              package: build-requirements:
              (builtins.getAttr package prev).overridePythonAttrs (old: {
                buildInputs =
                  (old.buildInputs or [ ])
                  ++ (builtins.map (
                    pkg: if builtins.isString pkg then builtins.getAttr pkg prev else pkg
                  ) build-requirements);
              })
            ) { markovify = [ "setuptools" ]; }
          );
        in
        {
          packages = rec {
            default = poetry2nix.mkPoetryApplication {
              inherit projectDir;
              inherit preferWheels;
              inherit overrides;
            };
            docker = pkgs.dockerTools.buildLayeredImage {
              name = "apollo";
              tag = "latest";
              contents = [ default ];
              config = {
                Cmd = [ "${default}/bin/apollo" ];
              };
            };
          };

          devenv.shells.default = {
            packages = with pkgs; [ poetry ];
            services.postgres = {
              enable = true;
              initialDatabases = [ { name = "apollo"; } ];
            };
            enterShell = ''
              # Create config files
              cp -n alembic.example.ini alembic.ini
              cp -n config.example.yaml config.yaml
            '';
            pre-commit = {
              excludes = [
                "migrations/versions"
                "__tests__"
              ];
              hooks = {
                # Nix
                nil.enable = true;
                nixfmt = {
                  enable = true;
                  package = pkgs.nixfmt-rfc-style;
                };

                # Python
                #poetry-check.enable = true;
                #poetry-lock.enable = true;
                #pyright.enable = true; # HUGE NIGHTMARE

                ruff = {
                  enable = true;
                  entry = "${pkgs.ruff}/bin/ruff check --fix";
                };

                black.enable = true;
              };
            };
          };
        };
    };
}
