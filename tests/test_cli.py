import prettymaps.cli as cli


def test_plot_command_calls_plot_with_parsed_args(monkeypatch):
    calls = []

    def fake_plot(query, preset=None, save_as=None, figsize=None, credit=None):
        calls.append(
            {
                "query": query,
                "preset": preset,
                "save_as": save_as,
                "figsize": figsize,
                "credit": credit,
            }
        )

    monkeypatch.setattr(cli, "_plot", fake_plot)

    cli.main(["plot", "Bom Fim, Porto Alegre, Brasil", "-o", "out.png"])

    assert calls == [
        {
            "query": "Bom Fim, Porto Alegre, Brasil",
            "preset": "default",
            "save_as": "out.png",
            "figsize": (11.7, 11.7),
            "credit": {},
        }
    ]


def test_plot_command_with_preset_and_size(monkeypatch):
    calls = []

    def fake_plot(query, preset=None, save_as=None, figsize=None, credit=None):
        calls.append(
            {
                "query": query,
                "preset": preset,
                "save_as": save_as,
                "figsize": figsize,
                "credit": credit,
            }
        )

    monkeypatch.setattr(cli, "_plot", fake_plot)

    cli.main(
        [
            "plot",
            "Rome, Italy",
            "--preset",
            "minimal",
            "-o",
            "rome.svg",
            "--width",
            "8",
            "--height",
            "10",
        ]
    )

    assert calls == [
        {
            "query": "Rome, Italy",
            "preset": "minimal",
            "save_as": "rome.svg",
            "figsize": (8.0, 10.0),
            "credit": {},
        }
    ]


def test_plot_command_with_no_credit_flag(monkeypatch):
    calls = []

    def fake_plot(query, preset=None, save_as=None, figsize=None, credit=None):
        calls.append(credit)

    monkeypatch.setattr(cli, "_plot", fake_plot)

    cli.main(["plot", "Rome, Italy", "-o", "rome.png", "--no-credit"])

    assert calls == [False]


def test_list_presets_prints_preset_names(capsys):
    cli.main(["list-presets"])

    out = capsys.readouterr().out
    assert "default" in out.splitlines()
