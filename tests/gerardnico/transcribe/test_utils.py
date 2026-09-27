from pathlib import Path


def get_tests_dir():
    """
    Return the test dir
    Why? Idea has no working stable directory, it's starting from the project
    directory if we run a package test and from the tests_dir if we are running a file/method tests
    :return:
    """
    current_file = Path(__file__).resolve()
    return current_file.parent.parent.parent
