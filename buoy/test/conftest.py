import pytest


def pytest_addoption(parser):
    parser.addoption("--host", default="localhost", help="buoy host")
    parser.addoption("--timeout", type=float, default=5.0, help="socket timeout (s)")


@pytest.fixture(scope="session")
def host(request):
    return request.config.getoption("--host")


@pytest.fixture(scope="session")
def timeout(request):
    return request.config.getoption("--timeout")
