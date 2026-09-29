"""Integration tests for the epmt explore command.

Translated from 020-explore.bats.
"""
import os
import pytest

from conftest import run_cmd

# Use a file-based SQLite database for persistence across epmt commands
EPMT_DB_PATH = "/tmp/epmt_explore_test.db"
EPMT_DB_URL  = f"sqlite:///{EPMT_DB_PATH}"


@pytest.fixture(autouse=True)
def setup_and_teardown(resource_path):
    """Setup: submit test data; Teardown: clean up."""
    env = {"EPMT_DB_URL": EPMT_DB_URL}
    jobs_in_module = "625151 627907 629322 633114 675992 680163 685000 685001 685003 685016 691209 692500 693129"

    # Clean up any existing test DB
    if os.path.exists(EPMT_DB_PATH):
        os.remove(EPMT_DB_PATH)

    # Delete pre-existing jobs
    run_cmd(f"epmt delete {jobs_in_module}", env=env)

    # Submit test data
    submit_files = (
        f"{resource_path}/test/data/submit/692500.tgz "
        f"{resource_path}/test/data/query/*.tgz "
        f"{resource_path}/test/data/outliers_nb/625151.tgz "
        f"{resource_path}/test/data/outliers_nb/627907.tgz "
        f"{resource_path}/test/data/outliers_nb/629322.tgz "
        f"{resource_path}/test/data/outliers_nb/633114.tgz "
        f"{resource_path}/test/data/outliers_nb/675992.tgz "
        f"{resource_path}/test/data/outliers_nb/680163.tgz "
        f"{resource_path}/test/data/outliers_nb/685001.tgz "
        f"{resource_path}/test/data/outliers_nb/691209.tgz "
        f"{resource_path}/test/data/outliers_nb/693129.tgz"
    )
    r = run_cmd(f"epmt submit {submit_files}", env=env)
    assert r.returncode == 0, f"Setup failed: epmt submit returned {r.returncode}: {r.stdout}\n{r.stderr}"

    # Force post-processing
    r = run_cmd(f"epmt dump {jobs_in_module}", env=env)
    assert r.returncode == 0, f"Setup failed: epmt dump returned {r.returncode}: {r.stdout}\n{r.stderr}"

    yield env

    # Teardown
    run_cmd(f"epmt delete {jobs_in_module}", env=env)
    if os.path.exists(EPMT_DB_PATH):
        os.remove(EPMT_DB_PATH)


class TestExplore:
    def test_epmt_explore(self, setup_and_teardown):
        """epmt explore should display experiment analysis (can take a couple of minutes)."""
        env = setup_and_teardown
        r = run_cmd("epmt explore ESM4_historical_D151", env=env)
        output = r.stdout + r.stderr
        assert "ocean_annual_z_1     18540101       625151      10425623185   ****" in output
        assert "ocean_annual_z_1     18590101       627907       6589174875" in output
        assert "ocean_annual_z_1     18890101       691209        860163243   ****" in output
        assert "ocean_annual_z_1     18940101       693129       3619324767     **" in output
        assert "18540101      10425623185" in output
        assert "18840101      26897098077   ****" in output
