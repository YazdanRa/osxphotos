import os

from click.testing import CliRunner

from osxphotos.cli import export

TEST_LIBRARY = "./tests/Test-iPhoto-Projects-10.15.7.photoslibrary"


def test_add_exported_to_album(monkeypatch):
    """Using option on non-macOS should error"""
    monkeypatch.setattr(export, "is_macos", False)
    
    runner = CliRunner()
    cwd = os.getcwd()

    result = runner.invoke(export, ["--help"])
    assert result.exit_code == 0
    assert "--add-exported-to-album" not in result.output
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "--add-exported-to-album",
                "SomeAlbum",
            ],
        )
        assert result.exit_code == 2
        assert "only works on macOS" in result.output

    monkeypatch.setattr(export, "is_macos", True)
    result = runner.invoke(export, ["--help"])
    assert result.exit_code == 0
    assert "--add-exported-to-album" in result.output
    with runner.isolated_filesystem():
        result = runner.invoke(
            export,
            [
                ".",
                "--library",
                os.path.join(cwd, TEST_LIBRARY),
                "--add-exported-to-album",
                "SomeAlbum",
            ],
        )
        assert result.exit_code == 0
