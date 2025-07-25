"""Tests which require user interaction to run for osxphotos timewarp command"""

import datetime
import os
import time

import pytest
from click.testing import CliRunner

from osxphotos import PhotosDB
from osxphotos.cli.timewarp import timewarp
from osxphotos.exiftool import ExifTool
from tests.conftest import get_os_version
from tests.parse_timewarp_output import (
    InspectValuesDateAdded,
    compare_inspect_output,
    parse_compare_exif,
    parse_inspect_output,
)

# set timezone to avoid issues with comparing dates
# @pytest.fixture(scope="module", autouse=True)
# def set_timezone():
#     """Set timezone to US/Pacific for all tests"""
#     old_tz = os.environ.get("TZ")
#     os.environ["TZ"] = "US/Pacific"
#     time.tzset()
#     yield
#     if old_tz:
#         os.environ["TZ"] = old_tz
#     else:
#         del os.environ["TZ"]
#     time.tzset()


TERMINAL_WIDTH = 250

OS_VER = get_os_version()
if int(OS_VER[0]) < 13:
    pytest.skip("These tests not implemented for macOS < 13", allow_module_level=True)

from tests.config_timewarp_ventura import UUID_DICT
from tests.config_timewarp_ventura import VENTURA_PHOTOS_5 as TEST_DATA


def say(msg: str) -> None:
    """Say message with text to speech"""
    os.system(f"say {msg}")


def ask_user_to_make_selection(
    photoslib, suspend_capture, photo_name: str, retry=3, video=False
) -> bool:
    """Ask user to make selection

    Args:
        photoslib: photoscript.PhotosLibrary instance passed from fixture
        suspend_capture: suspend capture fixture
        photo_name: name of the photo ask user for
        retry: number of times to retry before failing
        video: set to True if asking for a video instead of a photo
    """
    # needs to be called with a suspend_capture fixture
    photo_or_video = "video" if video else "photo"
    tries = 0
    while tries < retry:
        with suspend_capture:
            prompt = f"Select the {photo_or_video} of the {photo_name} then press Enter in the Terminal."
            say(prompt)
            input(f"\n{prompt}")

        selection = photoslib.selection
        if (
            len(selection) == 1
            and selection[0].filename == TEST_DATA["filenames"][photo_name]
        ):
            return True
        tries += 1
    return False


########## Interactive tests run first ##########


# @pytest.mark.timewarp
# def test_select_pears(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "pears")


@pytest.mark.timewarp
def test_inspect(photoslib, suspend_capture):
    """Test --inspect. NOTE: this test requires user interaction"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    values = parse_inspect_output(result.output)
    assert compare_inspect_output(TEST_DATA["inspect"]["expected"], values)


@pytest.mark.timewarp
def test_date(photoslib, suspend_capture):
    """Test --date"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--date",
            TEST_DATA["date"]["value"],
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    photo = next(photoslib.photos(uuid=[UUID_DICT["pears"]]))
    assert photo.date.date() == TEST_DATA["date"]["date"].date()


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["date_delta"]["parameters"])
def test_date_delta(photoslib, suspend_capture, input_value, expected):
    """Test --date-delta"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--date-delta",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["time"]["parameters"])
def test_time(photoslib, suspend_capture, input_value, expected):
    """Test --time"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--time", input_value, "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["time_delta"]["parameters"])
def test_time_delta(photoslib, suspend_capture, input_value, expected):
    """Test --time-delta"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--time-delta",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "input_value,expected_date,expected_tz", TEST_DATA["time_zone"]["parameters"]
)
def test_time_zone(
    photoslib, suspend_capture, input_value, expected_date, expected_tz, output_file
):
    """Test --time-zone"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--timezone", input_value, "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected_date
    assert output_values[0].tz_offset == expected_tz


@pytest.mark.timewarp
@pytest.mark.parametrize("expected", TEST_DATA["compare_exif"]["expected"])
def test_compare_exif(photoslib, suspend_capture, expected):
    """Test --compare-exif"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == expected


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "expected,album", TEST_DATA["compare_exif_add_to_album"]["expected"]
)
def test_compare_exif_add_to_album(photoslib, suspend_capture, expected, album):
    """Test --compare-exif --add-to-album"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--compare-exif",
            "--add-to-album",
            album,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert expected in result.output
    photo = next(photoslib.photos(uuid=[UUID_DICT["pears"]]))
    assert album in [album.name for album in photo.albums]


# @pytest.mark.timewarp
# def test_select_sunflowers(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "sunflowers")


@pytest.mark.timewarp
@pytest.mark.parametrize("expected", TEST_DATA["compare_exif_3"]["expected"])
def test_compare_exif_3(photoslib, suspend_capture, expected):
    """Test --compare-exif"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == expected


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["match"]["parameters"])
def test_match(photoslib, suspend_capture, input_value, expected):
    """Test --timezone --match"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--timezone",
            input_value,
            "--match-time",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
def test_match_dst(photoslib, suspend_capture):
    """Test --timezone --match-time for DST and named timezones, #1777"""

    runner = CliRunner()
    # init the date/time
    result = runner.invoke(
        timewarp,
        [
            "--time",
            "21:26:51",
            "--date",
            "2017-06-24",
            "--plain",
            "--force",
            "--timezone",
            "-0500",
            "--match-time",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz != "2017-06-24 21:26:51+0200"

    result = runner.invoke(
        timewarp,
        [
            "--timezone",
            "Europe/Madrid",
            "--match-time",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2017-06-24 21:26:51+0200"


@pytest.mark.timewarp
def test_match_no_dst(photoslib, suspend_capture):
    """Test --timezone --match-time when not in DST and named timezones, #1777"""

    runner = CliRunner()
    # init the date/time
    result = runner.invoke(
        timewarp,
        [
            "--time",
            "21:26:51",
            "--date",
            "2017-12-24",
            "--plain",
            "--force",
            "--timezone",
            "-0500",
            "--match-time",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz != "2017-12-24 21:26:51+0100"

    result = runner.invoke(
        timewarp,
        [
            "--timezone",
            "Europe/Madrid",
            "--match-time",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2017-12-24 21:26:51+0100"


@pytest.mark.timewarp
def test_time_delta_dst(photoslib, suspend_capture):
    """Test --timezone --time-delta with DST change #1839"""

    runner = CliRunner()
    # init the date/time
    result = runner.invoke(
        timewarp,
        [
            "--plain",
            "--force",
            "--verbose",
            "--date",
            "2024-03-31",
            "--time",
            "01:00:00",
            "--timezone",
            "Europe/Madrid",
            "--match-time",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2024-03-31 01:00:00+0100"

    result = runner.invoke(
        timewarp,
        [
            "--time-delta",
            "+1 hour",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2024-03-31 03:00:00+0200"


@pytest.mark.timewarp
def test_time_dst_change(photoslib, suspend_capture):
    """Test --time that forces a DST change"""

    runner = CliRunner()
    # init the date/time
    result = runner.invoke(
        timewarp,
        [
            "--plain",
            "--force",
            "--verbose",
            "--date",
            "2024-03-31",
            "--time",
            "01:00:00",
            "--timezone",
            "Europe/Madrid",
            "--match-time",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2024-03-31 01:00:00+0100"

    result = runner.invoke(
        timewarp,
        [
            "--time",
            "04:00:00",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunflowers"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == "2024-03-31 04:00:00+0200"


@pytest.mark.timewarp
def test_push_exif_missing_file():
    """Test --push-exif when an original file is missing"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--push-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["sunflowers"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "Skipping EXIF update for missing photo" in result.output


# @pytest.mark.timewarp
# def test_select_pumpkins(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "pumpkins")


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "match,tz_value,time_delta_value,expected_date,exif_date,exif_offset",
    TEST_DATA["exiftool"]["parameters"],
)
def test_push_exif_1(
    photoslib,
    match,
    tz_value,
    time_delta_value,
    expected_date,
    exif_date,
    exif_offset,
    output_file,
):
    """Test --timezone --match with --push-exif"""

    cli_args = [
        "--timezone",
        tz_value,
        "--time-delta",
        time_delta_value,
        "--push-exif",
        "--plain",
        "--force",
        "--uuid",
        UUID_DICT["pumpkins"],
    ]
    if match:
        cli_args.append("--match-time")

    runner = CliRunner()
    result = runner.invoke(timewarp, cli_args, terminal_width=TERMINAL_WIDTH)
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pumpkins"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected_date

    photo = next(photoslib.photos(uuid=[UUID_DICT["pumpkins"]]))
    uuid = photo.uuid
    path = PhotosDB().get_photo(uuid).path
    exif = ExifTool(path)
    exifdict = exif.asdict()
    assert exifdict["EXIF:DateTimeOriginal"] == exif_date
    assert exifdict["EXIF:OffsetTimeOriginal"] == exif_offset


# @pytest.mark.timewarp
# def test_select_pears_2(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "pears")


@pytest.mark.timewarp
def test_push_exif_2(photoslib, suspend_capture):
    """Test --push-exif"""
    pre_test = TEST_DATA["push_exif"]["pre"]
    post_test = TEST_DATA["push_exif"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        [
            "--push-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


@pytest.mark.timewarp
def test_pull_exif_1(photoslib, suspend_capture):
    """Test --pull-exif"""
    pre_test = TEST_DATA["pull_exif_1"]["pre"]
    post_test = TEST_DATA["pull_exif_1"]["post"]

    runner = CliRunner()

    # update the photo so we know if the data is updated
    result = runner.invoke(
        timewarp,
        [
            "-z",
            "-0400",
            "-D",
            "+1 day",
            "-m",
            "-V",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


# @pytest.mark.timewarp
# def test_select_apple_tree(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "apple tree")


@pytest.mark.timewarp
def test_pull_exif_no_time(photoslib, suspend_capture):
    """Test --pull-exif when photo has invalid date/time in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_time"]["pre"]
    post_test = TEST_DATA["pull_exif_no_time"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["apple_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["apple_tree"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["apple_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


# @pytest.mark.timewarp
# def test_select_marigolds(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "marigold flowers")


@pytest.mark.timewarp
def test_pull_exif_no_offset(photoslib, suspend_capture):
    """Test --pull-exif when photo has no offset in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_offset"]["pre"]
    post_test = TEST_DATA["pull_exif_no_offset"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["marigolds"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["marigolds"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["marigolds"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


# @pytest.mark.timewarp
# def test_select_zinnias(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(
#         photoslib, suspend_capture, "multi-colored zinnia flowers"
#     )


@pytest.mark.timewarp
def test_pull_exif_no_data(photoslib, suspend_capture):
    """Test --pull-exif when photo has no data in EXIF"""
    pre_test = TEST_DATA["pull_exif_no_data"]["pre"]
    post_test = TEST_DATA["pull_exif_no_data"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["zinnias"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["zinnias"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "Skipping update for missing EXIF data in photo" in result.output

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["zinnias"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


@pytest.mark.timewarp
def test_pull_exif_no_data_use_file_time(photoslib, suspend_capture):
    """Test --pull-exif when photo has no data in EXIF with --use-file-time"""
    pre_test = TEST_DATA["pull_exif_no_data_use_file_time"]["pre"]
    post_test = TEST_DATA["pull_exif_no_data_use_file_time"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["zinnias"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--use-file-time",
            "--uuid",
            UUID_DICT["zinnias"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    assert "EXIF date/time missing, using file modify date/time" in result.output

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["zinnias"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


# @pytest.mark.timewarp
# def test_select_sunset_video(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "sunset", video=True)


@pytest.mark.timewarp
@pytest.mark.parametrize("expected", TEST_DATA["compare_video_1"]["expected"])
def test_video_compare_exif(photoslib, suspend_capture, expected):
    """Test --compare-exif with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == expected


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "input_value,expected", TEST_DATA["video_date_delta"]["parameters"]
)
def test_video_date_delta(
    photoslib, suspend_capture, input_value, expected, output_file
):
    """Test --date-delta with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--date-delta",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "input_value,expected", TEST_DATA["video_time_delta"]["parameters"]
)
def test_video_time_delta(
    photoslib, suspend_capture, input_value, expected, output_file
):
    """Test --time-delta with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--time-delta",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_date"]["parameters"])
def test_video_date(photoslib, suspend_capture, input_value, expected):
    """Test --date with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--date",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_time"]["parameters"])
def test_video_time(photoslib, suspend_capture, input_value, expected):
    """Test --time with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--time",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    # inspect to get the updated times
    # don't use photo.date as it will return local time instead of the time in the timezone
    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "input_value,expected_date,expected_tz", TEST_DATA["video_time_zone"]["parameters"]
)
def test_video_time_zone(
    photoslib, suspend_capture, input_value, expected_date, expected_tz, output_file
):
    """Test --time-zone"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--timezone",
            input_value,
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected_date
    assert output_values[0].tz_offset == expected_tz


@pytest.mark.timewarp
@pytest.mark.parametrize("input_value,expected", TEST_DATA["video_match"]["parameters"])
def test_video_match(photoslib, suspend_capture, input_value, expected):
    """Test --timezone --match with video"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--timezone",
            input_value,
            "--match-time",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert output_values[0].date_tz == expected


@pytest.mark.timewarp
def test_video_push_exif(photoslib, suspend_capture):
    """Test --push-exif with video"""
    pre_test = TEST_DATA["video_push_exif"]["pre"]
    post_test = TEST_DATA["video_push_exif"]["post"]

    runner = CliRunner()

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--push-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


@pytest.mark.timewarp
def test_video_pull_exif(photoslib, suspend_capture):
    """Test --pull-exif with video"""
    pre_test = TEST_DATA["video_pull_exif"]["pre"]
    post_test = TEST_DATA["video_pull_exif"]["post"]

    runner = CliRunner()

    # update the photo so we know if the data is updated
    result = runner.invoke(
        timewarp,
        [
            "-z",
            "-0500",
            "-D",
            "+1 day",
            "-T",
            "-10 hours",
            "-m",
            "-V",
            "--plain",
            "--force",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == pre_test

    result = runner.invoke(
        timewarp,
        [
            "--pull-exif",
            "--plain",
            "--force",
            "--verbose",
            "--uuid",
            UUID_DICT["sunset_video"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--compare-exif", "--plain", "--force", "--uuid", UUID_DICT["sunset_video"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_compare_exif(result.output)
    assert output_values[0] == post_test


# @pytest.mark.timewarp
# def test_select_pears_3(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "pears")


@pytest.mark.timewarp
def test_function(photoslib, suspend_capture):
    """Test timewarp function"""

    expected = TEST_DATA["function"]["expected"]

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--function",
            "tests/timewarp_function_example.py::get_date_time_timezone",
            "--force",
            "--uuid",
            UUID_DICT["pears"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["pears"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert compare_inspect_output(output_values[0], expected)


# @pytest.mark.timewarp
# def test_select_palm_tree_1(photoslib, suspend_capture):
#     """Force user to select the right photo for following tests"""
#     assert ask_user_to_make_selection(photoslib, suspend_capture, "palm tree")


@pytest.mark.timewarp
def test_parse_date(photoslib, suspend_capture):
    """Test --parse-date"""

    expected = TEST_DATA["parse_date"]["expected"]

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--parse-date", "^%Y%m%d_%H%M%S", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert compare_inspect_output(output_values[0], expected)


@pytest.mark.timewarp
def test_parse_date_tz(photoslib, suspend_capture):
    """Test --parse-date with a timezone"""

    expected = TEST_DATA["parse_date_tz"]["expected"]

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        [
            "--parse-date",
            "^%Y%m%d_%H%M%S%z",
            "--force",
            "--uuid",
            UUID_DICT["palm_tree"],
        ],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output)
    assert compare_inspect_output(output_values[0], expected)


@pytest.mark.timewarp
@pytest.mark.parametrize(
    "date_added,expected",
    TEST_DATA["date_added"]["data"],
)
def test_date_added(
    photoslib, suspend_capture, date_added: str, expected: InspectValuesDateAdded
):
    """Test --date-added"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--date-added", date_added, "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output, date_added=True)
    assert compare_inspect_output(output_values[0], expected)


@pytest.mark.timewarp
def test_date_added_from_photo(photoslib, suspend_capture):
    """Test --date-added-from-photo"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--date-added-from-photo", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["palm_tree"]],
        terminal_width=TERMINAL_WIDTH,
    )
    output_values = parse_inspect_output(result.output, date_added=True)
    expected = TEST_DATA["date_added_from_photo"]["expected"]
    assert compare_inspect_output(output_values[0], expected)


@pytest.mark.timewarp
def test_reset(photoslib, suspend_capture):
    """Test --reset"""

    runner = CliRunner()
    result = runner.invoke(
        timewarp,
        ["--reset", "--plain", "--force", "--uuid", UUID_DICT["water_lily"]],
        terminal_width=TERMINAL_WIDTH,
    )
    assert result.exit_code == 0
    time.sleep(1)

    result = runner.invoke(
        timewarp,
        ["--inspect", "--plain", "--force", "--uuid", UUID_DICT["water_lily"]],
        terminal_width=TERMINAL_WIDTH,
    )
    values = parse_inspect_output(result.output)
    assert compare_inspect_output(TEST_DATA["reset"]["expected"], values)
