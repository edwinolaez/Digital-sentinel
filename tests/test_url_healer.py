import json
import pytest
import digital_sentinel.tools.url_healer as healer


@pytest.fixture(autouse=True)
def patch_paths(tmp_path, monkeypatch):
    monkeypatch.setattr(healer, "_OVERRIDES_PATH", str(tmp_path / "career_url_overrides.json"))
    monkeypatch.setattr(healer, "_SNAPSHOT_PATH", str(tmp_path / "career_page_snapshots.json"))


class TestSlug:
    def test_simple_name(self):
        assert healer._slug("NeoFinancial") == "neofinancial"

    def test_spaces_removed(self):
        assert healer._slug("Bold Commerce") == "boldcommerce"

    def test_dots_removed(self):
        assert healer._slug("F12.net") == "f12net"

    def test_numbers_kept(self):
        assert healer._slug("1Password") == "1password"

    def test_hyphens_removed(self):
        assert healer._slug("Sure-Systems") == "suresystems"


class TestUpdateCareerPageUrl:
    def test_saves_new_override(self):
        healer.update_career_page_url("Benevity", "https://benevity.com/careers")
        overrides = json.loads(open(healer._OVERRIDES_PATH).read())
        assert overrides["Benevity"] == "https://benevity.com/careers"

    def test_confirmation_message_returned(self):
        result = healer.update_career_page_url("Helcim", "https://helcim.com/careers")
        assert "saved" in result.lower()

    def test_shows_old_and_new_url(self):
        healer.update_career_page_url("Helcim", "https://helcim.com/old")
        result = healer.update_career_page_url("Helcim", "https://helcim.com/new")
        assert "https://helcim.com/old" in result
        assert "https://helcim.com/new" in result

    def test_overwrites_existing_entry(self):
        healer.update_career_page_url("Jobber", "https://jobber.com/v1")
        healer.update_career_page_url("Jobber", "https://jobber.com/v2")
        overrides = json.loads(open(healer._OVERRIDES_PATH).read())
        assert overrides["Jobber"] == "https://jobber.com/v2"

    def test_multiple_companies_saved(self):
        healer.update_career_page_url("A", "https://a.com/careers")
        healer.update_career_page_url("B", "https://b.com/careers")
        overrides = json.loads(open(healer._OVERRIDES_PATH).read())
        assert len(overrides) == 2


class TestListUrlOverrides:
    def test_empty_returns_no_overrides_message(self):
        result = healer.list_url_overrides()
        assert "no url overrides" in result.lower()

    def test_lists_saved_company_and_url(self):
        healer.update_career_page_url("Arcurve", "https://arcurve.com/careers")
        result = healer.list_url_overrides()
        assert "Arcurve" in result
        assert "https://arcurve.com/careers" in result

    def test_count_shown_in_output(self):
        healer.update_career_page_url("A", "https://a.com/careers")
        healer.update_career_page_url("B", "https://b.com/careers")
        result = healer.list_url_overrides()
        assert "2" in result


class TestGetBrokenCareerUrls:
    def test_no_snapshot_returns_message(self):
        result = healer.get_broken_career_urls()
        assert "no snapshot" in result.lower()

    def test_no_errors_in_snapshot(self):
        snapshot = {"Benevity": {"url": "https://benevity.com/careers", "hash": "abc123"}}
        with open(healer._SNAPSHOT_PATH, "w") as f:
            json.dump(snapshot, f)
        result = healer.get_broken_career_urls()
        assert "no broken" in result.lower()

    def test_broken_url_reported(self):
        snapshot = {
            "Symend": {"url": "https://symend.com/jobs", "error": "404 Not Found"},
        }
        with open(healer._SNAPSHOT_PATH, "w") as f:
            json.dump(snapshot, f)
        result = healer.get_broken_career_urls()
        assert "Symend" in result
        assert "404" in result

    def test_healthy_company_not_in_broken_list(self):
        snapshot = {
            "Symend": {"url": "https://symend.com/jobs", "error": "404 Not Found"},
            "Attabotics": {"url": "https://attabotics.com/careers", "hash": "xyz"},
        }
        with open(healer._SNAPSHOT_PATH, "w") as f:
            json.dump(snapshot, f)
        result = healer.get_broken_career_urls()
        assert "Attabotics" not in result
