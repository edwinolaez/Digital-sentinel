import json
import os
import pytest
import digital_sentinel.tools.profile_manager as pm


@pytest.fixture(autouse=True)
def patch_profile_path(tmp_path, monkeypatch):
    monkeypatch.setattr(pm, "_PROFILE_PATH", str(tmp_path / "profile.json"))


class TestGetProfile:
    def test_returns_string(self):
        assert isinstance(pm.get_profile(), str)

    def test_contains_default_name(self):
        assert "Edwin Olaez" in pm.get_profile()

    def test_creates_profile_file_on_first_call(self):
        pm.get_profile()
        assert os.path.exists(pm._PROFILE_PATH)

    def test_contains_education_section(self):
        assert "SAIT" in pm.get_profile()


class TestSetProfileField:
    def test_set_linkedin(self):
        pm.set_profile_field("personal.linkedin", "https://linkedin.com/in/edwinolaez")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        assert profile["personal"]["linkedin"] == "https://linkedin.com/in/edwinolaez"

    def test_set_notes_top_level(self):
        result = pm.set_profile_field("notes", "Actively seeking roles")
        assert "Updated" in result
        profile = json.loads(open(pm._PROFILE_PATH).read())
        assert profile["notes"] == "Actively seeking roles"

    def test_returns_confirmation(self):
        result = pm.set_profile_field("personal.github", "https://github.com/edwinolaez")
        assert "Updated" in result

    def test_invalid_path_returns_error(self):
        result = pm.set_profile_field("personal.nonexistent_field", "value")
        assert "not found" in result.lower() or "could not find" in result.lower()

    def test_invalid_top_level_key(self):
        result = pm.set_profile_field("nonexistent_key", "value")
        assert "not found" in result.lower()


class TestAddToList:
    def test_add_new_language(self):
        pm.add_to_list("skills.languages", "Go")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        assert "Go" in profile["skills"]["languages"]

    def test_returns_added_confirmation(self):
        result = pm.add_to_list("skills.tools", "Docker")
        assert "Added" in result

    def test_duplicate_rejected(self):
        pm.add_to_list("skills.languages", "Rust")
        result = pm.add_to_list("skills.languages", "Rust")
        assert "already in" in result.lower()

    def test_invalid_path_returns_error(self):
        result = pm.add_to_list("skills.nonexistent", "item")
        assert "not found" in result.lower()

    def test_non_list_field_returns_error(self):
        result = pm.add_to_list("personal.name", "something")
        assert "not a list" in result.lower()

    def test_add_to_target_roles(self):
        result = pm.add_to_list("goals.target_roles", "Junior Backend Developer")
        assert "Added" in result


class TestRemoveFromList:
    def test_remove_existing_item(self):
        pm.add_to_list("skills.languages", "Ruby")
        pm.remove_from_list("skills.languages", "Ruby")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        assert "Ruby" not in profile["skills"]["languages"]

    def test_returns_removed_confirmation(self):
        pm.add_to_list("skills.languages", "Elixir")
        result = pm.remove_from_list("skills.languages", "Elixir")
        assert "Removed" in result

    def test_remove_nonexistent_item_returns_error(self):
        result = pm.remove_from_list("skills.languages", "COBOL")
        assert "not found" in result.lower()


class TestAddProject:
    def test_add_new_project(self):
        pm.add_project("Test App", "A test application", "Python, React")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        names = [p["name"] for p in profile["projects"]]
        assert "Test App" in names

    def test_returns_added_confirmation(self):
        result = pm.add_project("My App", "desc", "Python")
        assert "added" in result.lower()

    def test_duplicate_project_rejected(self):
        pm.add_project("Duplicate", "desc", "Python")
        result = pm.add_project("Duplicate", "desc2", "Go")
        assert "already exists" in result.lower()

    def test_tech_parsed_as_list(self):
        pm.add_project("Tech Test", "desc", "Python, Go, Rust")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        proj = next(p for p in profile["projects"] if p["name"] == "Tech Test")
        assert proj["tech"] == ["Python", "Go", "Rust"]

    def test_optional_url_and_highlights(self):
        pm.add_project("Full App", "desc", "Python", url="https://github.com/test", highlights="Fast, Reliable")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        proj = next(p for p in profile["projects"] if p["name"] == "Full App")
        assert proj["url"] == "https://github.com/test"
        assert proj["highlights"] == ["Fast", "Reliable"]


class TestUpdateProject:
    def test_update_description(self):
        pm.add_project("My App", "old desc", "Python")
        pm.update_project("My App", "description", "new desc")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        proj = next(p for p in profile["projects"] if p["name"] == "My App")
        assert proj["description"] == "new desc"

    def test_update_tech_parsed_as_list(self):
        pm.add_project("Tech App", "desc", "Python")
        pm.update_project("Tech App", "tech", "Go, Rust, TypeScript")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        proj = next(p for p in profile["projects"] if p["name"] == "Tech App")
        assert proj["tech"] == ["Go", "Rust", "TypeScript"]

    def test_update_url(self):
        pm.add_project("URL App", "desc", "Python")
        pm.update_project("URL App", "url", "https://github.com/test")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        proj = next(p for p in profile["projects"] if p["name"] == "URL App")
        assert proj["url"] == "https://github.com/test"

    def test_invalid_field_returns_error(self):
        pm.add_project("Field App", "desc", "Python")
        result = pm.update_project("Field App", "invalid_field", "value")
        assert "unknown" in result.lower()

    def test_nonexistent_project_returns_error(self):
        result = pm.update_project("Ghost Project", "description", "value")
        assert "not found" in result.lower()


class TestRemoveProject:
    def test_remove_existing_project(self):
        pm.add_project("Remove Me", "desc", "Python")
        pm.remove_project("Remove Me")
        profile = json.loads(open(pm._PROFILE_PATH).read())
        assert "Remove Me" not in [p["name"] for p in profile["projects"]]

    def test_returns_removed_confirmation(self):
        pm.add_project("Gone", "desc", "Python")
        result = pm.remove_project("Gone")
        assert "removed" in result.lower()

    def test_remove_nonexistent_returns_error(self):
        result = pm.remove_project("Ghost")
        assert "not found" in result.lower()

    def test_case_insensitive_match(self):
        pm.add_project("CaseSensitive", "desc", "Python")
        result = pm.remove_project("casesensitive")
        assert "removed" in result.lower()
