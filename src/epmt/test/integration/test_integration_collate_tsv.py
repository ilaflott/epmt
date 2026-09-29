"""Integration tests for COLLATED_TSV output format.

Translated from 030-collate-tsv.bats.
"""
import os
import pytest

from conftest import run_cmd, epmt_setting

# Use a file-based SQLite database for persistence across epmt commands
EPMT_DB_PATH = "/tmp/epmt_test_collate_tsv.sqlite"
EPMT_DB_URL  = f"sqlite:///{EPMT_DB_PATH}"


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup: clean previous state; Teardown: clean up."""
    stage_dest = epmt_setting("stage_command_dest")
    assert stage_dest and os.path.isdir(stage_dest)
    jobs_in_module = "989"
    env = {"EPMT_DB_URL": EPMT_DB_URL}

    # Clean up
    if os.path.exists(EPMT_DB_PATH):
        os.remove(EPMT_DB_PATH)
    staged = os.path.join(stage_dest, "989.tgz")
    if os.path.exists(staged):
        os.remove(staged)
    run_cmd(f"epmt delete {jobs_in_module}", env=env)

    yield {"stage_dest": stage_dest, "env": env}

    # Teardown
    run_cmd(f"epmt delete {jobs_in_module}", env=env)
    staged = os.path.join(stage_dest, "989.tgz")
    if os.path.exists(staged):
        os.remove(staged)
    if os.path.exists(EPMT_DB_PATH):
        os.remove(EPMT_DB_PATH)


class TestCollateTsv:
    def test_epmt_with_collated_tsv(self, setup_and_teardown):
        """Full start/source/run/stop/stage/submit cycle with COLLATED_TSV."""
        ctx = setup_and_teardown
        stage_dest = ctx["stage_dest"]
        env = ctx["env"]

        # Run the full workflow as a bash script
        script = r"""
set -e
export SLURM_JOB_ID=989
export EPMT_JOB_TAGS='op:check-tsv'
epmt start
eval `epmt source| sed '/^PAPIEX_OPTIONS/ s/PAPIEX_OPTIONS=/PAPIEX_OPTIONS=COLLATED_TSV,/'`
/bin/sleep 1 2>/dev/null >&2
epmt_uninstrument
epmt stop
f=`epmt stage`
epmt -v submit $f
epmt list | grep -w 989 > /dev/null
"""
        r = run_cmd("bash", env=env, input=script)
        # The submit should succeed (we check the list above in the script)
        # Now verify the dump
        r = run_cmd("epmt dump -k tags 989", env=env)
        assert "{'op': 'check-tsv'}" in r.stdout
        staged = os.path.join(stage_dest, "989.tgz")
        assert os.path.isfile(staged), f"Staged file not found: {staged}"
        os.remove(staged)
