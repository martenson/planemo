import contextlib
import os

from .config import galaxy_config
from .run import (
    setup_venv,
    run_galaxy_command,
)
from planemo import io


def serve(ctx, paths, **kwds):
    # TODO: Preceate a user.
    # TODO: Setup an admin user.
    # TODO: Pass through more parameters.
    # TODO: Populate test-data directory as FTP directory.
    daemon = kwds.get("daemon", False)
    if daemon:
        kwds["no_cleanup"] = True

    with galaxy_config(ctx, paths, **kwds) as config:
        # TODO: Allow running dockerized Galaxy here instead.
        setup_venv_command = setup_venv(ctx, kwds)
        run_script = os.path.join(config.galaxy_root, "run.sh")
        run_script += " $COMMON_STARTUP_ARGS"
        if daemon:
            run_script += " --daemon --wait"
            config.env["GALAXY_RUN_ALL"] = "1"
        else:
            run_script += " --server-name '%s' --reload" % config.server_name
        server_ini = os.path.join(config.config_directory, "galaxy.ini")
        config.env["GALAXY_CONFIG_FILE"] = server_ini
        cd_to_galaxy_command = "cd %s" % config.galaxy_root
        cmd = io.shell_join(
            cd_to_galaxy_command,
            setup_venv_command,
            run_script,
        )
        action = "Starting galaxy"
        run_galaxy_command(
            ctx,
            cmd,
            config.env,
            action,
        )
        return config


@contextlib.contextmanager
def shed_serve(ctx, install_args_list, **kwds):
    with serve_daemon(ctx, **kwds) as config:
        install_deps = not kwds.get("skip_dependencies", False)
        io.info("Installing repositories - this may take some time...")
        for install_args in install_args_list:
            install_args["install_tool_dependencies"] = install_deps
            install_args["install_repository_dependencies"] = True
            install_args["new_tool_panel_section_label"] = "Shed Installs"
            config.install_repo(
                **install_args
            )
        config.wait_for_all_installed()
        yield config


@contextlib.contextmanager
def serve_daemon(ctx, paths=[], **kwds):
    config = None
    try:
        config = serve(ctx, paths, daemon=True, **kwds)
        yield config
    finally:
        if config:
            config.kill()
            if not kwds.get("no_cleanup", False):
                config.cleanup()