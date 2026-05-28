from digital_sentinel.tools.scam_detector import (
    check_url_safety,
    format_safety_report,
    scan_for_scam_signals,
)


class TestCheckUrlSafety:
    def test_known_safe_domain(self):
        result = check_url_safety("https://linkedin.com/jobs/123")
        assert result["safe"] is True
        assert result["risk"] == "SAFE"
        assert result["reasons"] == []

    def test_subdomain_of_safe_domain(self):
        result = check_url_safety("https://boards.greenhouse.io/company/job123")
        assert result["safe"] is True
        assert result["risk"] == "SAFE"

    def test_www_prefix_stripped(self):
        result = check_url_safety("https://www.linkedin.com/jobs")
        assert result["safe"] is True

    def test_canada_job_bank(self):
        result = check_url_safety("https://www.jobbank.gc.ca/jobsearch")
        assert result["safe"] is True

    def test_suspicious_tld(self):
        result = check_url_safety("https://jobs.xyz/apply")
        assert result["risk"] == "SUSPICIOUS"
        assert any("TLD" in r for r in result["reasons"])

    def test_http_not_https(self):
        result = check_url_safety("http://someunknowncompany.com/jobs")
        assert result["risk"] == "SUSPICIOUS"
        assert any("HTTP" in r for r in result["reasons"])

    def test_typosquatting(self):
        # Domain contains the substring "linkedin" but isn't the real site
        result = check_url_safety("https://linkedin-jobs-apply.com/jobs")
        assert result["risk"] == "SUSPICIOUS"
        assert any("typosquat" in r.lower() for r in result["reasons"])

    def test_long_domain_flagged(self):
        long_domain = "a" * 41 + ".com"
        result = check_url_safety(f"https://{long_domain}/jobs")
        assert result["risk"] == "SUSPICIOUS"
        assert any("long" in r.lower() for r in result["reasons"])

    def test_hyphen_heavy_domain_flagged(self):
        result = check_url_safety("https://get-a-job-now-fast-hire.com/apply")
        assert result["risk"] == "SUSPICIOUS"
        assert any("hyphen" in r.lower() for r in result["reasons"])

    def test_unknown_domain_no_flags(self):
        result = check_url_safety("https://legitimatecompany.com/careers")
        assert result["safe"] is False
        assert result["risk"] == "UNKNOWN"
        assert result["reasons"] == []

    def test_unparseable_url_does_not_crash(self):
        result = check_url_safety("not_a_url_at_all!!!")
        assert "safe" in result
        assert "risk" in result


class TestScanForScamSignals:
    def test_clear_legitimate_posting(self):
        text = "Junior Software Developer at Acme Corp. Python required. Competitive salary."
        result = scan_for_scam_signals(text)
        assert result["risk"] == "CLEAR"
        assert result["strong_hits"] == []
        assert result["soft_hits"] == []

    def test_strong_signal_bitcoin(self):
        result = scan_for_scam_signals("Get paid in Bitcoin — earn $500 per day working from home!")
        assert result["risk"] == "SCAM"
        assert len(result["strong_hits"]) > 0

    def test_strong_signal_gift_card(self):
        result = scan_for_scam_signals("Buy gift cards to start. No interview required.")
        assert result["risk"] == "SCAM"

    def test_strong_signal_wire_transfer(self):
        result = scan_for_scam_signals("You'll need to send a wire transfer to secure your position.")
        assert result["risk"] == "SCAM"

    def test_strong_signal_mlm(self):
        result = scan_for_scam_signals("Join our MLM — be your own boss with unlimited earning potential!")
        assert result["risk"] == "SCAM"

    def test_single_soft_signal_is_caution(self):
        result = scan_for_scam_signals("Urgent hiring — flexible hours position available now.")
        assert result["risk"] == "CAUTION"
        assert len(result["soft_hits"]) >= 1

    def test_multiple_soft_signals_is_caution(self):
        # 3 soft signals, no strong ones (avoids "work from home" + "no experience" combo which is a strong hit)
        result = scan_for_scam_signals(
            "Urgent hiring available. Financial freedom awaits. Passive income opportunity."
        )
        assert result["risk"] == "CAUTION"
        assert len(result["soft_hits"]) >= 3

    def test_summary_always_present(self):
        result = scan_for_scam_signals("Normal software engineer job posting.")
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_result_has_all_keys(self):
        result = scan_for_scam_signals("test")
        assert set(result.keys()) == {"risk", "strong_hits", "soft_hits", "summary"}


class TestFormatSafetyReport:
    def test_all_clear_contains_safe_and_clear(self):
        url_result = {"risk": "SAFE", "reasons": [], "safe": True}
        scam_result = {"risk": "CLEAR", "strong_hits": [], "soft_hits": [], "summary": "CLEAR"}
        report = format_safety_report(url_result, scam_result)
        assert "SAFE" in report
        assert "CLEAR" in report

    def test_suspicious_url_shows_reasons(self):
        url_result = {"risk": "SUSPICIOUS", "reasons": ["Uses HTTP (not HTTPS) — no encryption"], "safe": False}
        scam_result = {"risk": "CLEAR", "strong_hits": [], "soft_hits": [], "summary": "CLEAR"}
        report = format_safety_report(url_result, scam_result)
        assert "HTTP" in report

    def test_scam_hits_shown_in_report(self):
        url_result = {"risk": "SAFE", "reasons": [], "safe": True}
        scam_result = {
            "risk": "SCAM",
            "strong_hits": [r"\\bbitcoin\\b"],
            "soft_hits": [],
            "summary": "SCAM",
        }
        report = format_safety_report(url_result, scam_result)
        assert "SCAM" in report
